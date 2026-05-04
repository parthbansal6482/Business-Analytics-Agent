"""
Data Retriever: embeds the query and searches all Qdrant collections.
Deep Mode uses DEEP_MODE_TOP_K chunks and LLM-based review reranking.
Quick Mode uses QUICK_MODE_TOP_K chunks only.
All config values are read from environment variables.
"""

import os
import re
import json
import logging

from agent.state import AgentState
from data.embedder import embed_one
from memory.qdrant_store import search, client as qdrant_client
from qdrant_client.models import Filter, FieldCondition, MatchValue
from utils.sse import publish_step
from utils.llm import call_llm_with_retry, count_tokens

logger = logging.getLogger(__name__)

QUICK_TOP_K  = int(os.getenv("QUICK_MODE_TOP_K", "10"))
DEEP_TOP_K   = int(os.getenv("DEEP_MODE_TOP_K",  "30"))
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K",     "15"))


def rerank_reviews(query: str, review_chunks: list[str]) -> tuple[list[str], int]:
    """LLM-based review reranking — only used in Deep Mode."""
    if len(review_chunks) <= RERANK_TOP_K:
        return review_chunks, 0

    rerank_prompt = f"""You are filtering customer reviews for relevance to a business question.

BUSINESS QUESTION: "{query}"

Score each review 1-10 for relevance to the question above:
  10 = Directly answers the question with specific details
  7-9 = Highly relevant, contains useful signals
  4-6 = Somewhat relevant
  1-3 = Not relevant to this specific question

Reviews:
{chr(10).join(f"[{i+1}] {chunk}" for i, chunk in enumerate(review_chunks))}

Return ONLY a JSON array of the top {RERANK_TOP_K} review numbers ordered by relevance. Example: [3, 7, 1, 12, 5]
No explanation. Just the JSON array."""

    try:
        result = call_llm_with_retry(rerank_prompt)
        match = re.search(r'\[[\d,\s]+\]', result)
        if match:
            indices = json.loads(match.group())
            reranked = [
                review_chunks[i - 1]
                for i in indices
                if isinstance(i, int) and 0 < i <= len(review_chunks)
            ]
            if reranked:
                logger.info(f"Review reranking: {len(review_chunks)} -> {len(reranked)} chunks")
                tokens = count_tokens(rerank_prompt) + count_tokens(result)
                return reranked, tokens
    except Exception as e:
        logger.warning(f"Review reranking failed (using top-K fallback): {e}")

    return review_chunks[:RERANK_TOP_K], 0


SALES_KEYWORDS = re.compile(
    r'\b(best.?sell|top.?product|top.?sku|highest.?sales|most.?sold|'
    r'best.?performer|sales.?rank|top.?seller|revenue.?leader)\b',
    re.IGNORECASE
)


def _get_sales_ranked_catalog(user_id: str, top_n: int = 20) -> list[str]:
    """
    Scroll the full catalog and return top N products sorted by sales_volume.
    Used for sales-intent queries where cosine search won't find best sellers.
    """
    try:
        results, _ = qdrant_client.scroll(
            collection_name="ecomm_catalog",
            scroll_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
            limit=500,
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            return []

        def _sales_vol(point):
            v = point.payload.get("sales_volume", 0)
            try:
                return float(v) if v not in ("", None) else 0.0
            except (TypeError, ValueError):
                return 0.0

        sorted_points = sorted(results, key=_sales_vol, reverse=True)
        return [p.payload.get("text", "") for p in sorted_points[:top_n] if p.payload.get("text")]
    except Exception as e:
        logger.warning(f"sales-ranked catalog fetch failed: {e}")
        return []


def data_retriever(state: AgentState) -> AgentState:
    try:
        query      = state["query"]
        user_id    = state["user_id"]
        session_id = state["session_id"]
        mode       = state.get("mode", "quick")
        # Use the same high limit for both modes to ensure consistency
        top_k = DEEP_TOP_K

        # Embed once, reuse across all searches
        query_vec = embed_one(query)

        catalog_res    = search("ecomm_catalog",     query_vec, user_id, top_k=top_k)
        review_res     = search("ecomm_reviews",     query_vec, user_id, top_k=top_k)
        pricing_res    = search("ecomm_pricing",     query_vec, user_id, top_k=top_k)
        competitor_res = search("ecomm_competitors", query_vec, user_id, top_k=top_k)
        order_res      = search("ecomm_orders",      query_vec, user_id, top_k=top_k)
        customer_res   = search("ecomm_customers",   query_vec, user_id, top_k=top_k)

        catalog_chunks    = [r["text"] for r in catalog_res    if r.get("text")]
        review_chunks     = [r["text"] for r in review_res     if r.get("text")]
        pricing_chunks    = [r["text"] for r in pricing_res    if r.get("text")]
        competitor_chunks = [r["text"] for r in competitor_res if r.get("text")]
        order_chunks      = [r["text"] for r in order_res      if r.get("text")]
        customer_chunks   = [r["text"] for r in customer_res   if r.get("text")]

        # For sales-intent queries, prepend sales-ranked products so the LLM
        # always sees actual best sellers — not just semantically similar ones.
        if SALES_KEYWORDS.search(query):
            sales_ranked = _get_sales_ranked_catalog(user_id, top_n=20)
            if sales_ranked:
                # Deduplicate: keep sales-ranked first, append any extras from semantic search
                seen = set(sales_ranked)
                extra = [c for c in catalog_chunks if c not in seen]
                catalog_chunks = sales_ranked + extra
                logger.info(f"Sales-intent query: prepended {len(sales_ranked)} sales-ranked products")

        # Deep Mode: LLM-based review reranking for higher signal quality
        tokens_rerank = 0
        if mode == "deep" and review_chunks:
            review_chunks, tokens_rerank = rerank_reviews(query, review_chunks)

        logger.info(
            f"Retrieved ({mode}): catalog={len(catalog_chunks)} reviews={len(review_chunks)} "
            f"pricing={len(pricing_chunks)} competitors={len(competitor_chunks)} "
            f"orders={len(order_chunks)} customers={len(customer_chunks)}"
        )

        publish_step(
            session_id,
            "retrieve",
            "done",
            (
                f"Found {len(catalog_chunks)} products, "
                f"{len(review_chunks)} reviews, "
                f"{len(pricing_chunks)} pricing records, "
                f"{len(competitor_chunks)} competitor listings"
            ),
        )

        total_chunks = (
            len(catalog_chunks) + len(review_chunks) + len(pricing_chunks)
            + len(competitor_chunks) + len(order_chunks) + len(customer_chunks)
        )
        if total_chunks == 0:
            question = (
                "I don't have any data for your account yet. "
                "Please upload your product catalog, reviews, pricing, "
                "or competitor data first."
            )
            publish_step(session_id, "clarify", "clarification", question)
            return {
                **state,
                "catalog_chunks": [],
                "review_chunks": [],
                "pricing_chunks": [],
                "competitor_chunks": [],
                "order_chunks": [],
                "customer_chunks": [],
                "error": "NO_DATA",
                "needs_clarification": True,
                "clarification_question": question,
                "completed_nodes": [*state.get("completed_nodes", []), "data_retriever"],
            }

        return {
            **state,
            "catalog_chunks":    catalog_chunks,
            "review_chunks":     review_chunks,
            "pricing_chunks":    pricing_chunks,
            "competitor_chunks": competitor_chunks,
            "order_chunks":      order_chunks,
            "customer_chunks":   customer_chunks,
            "total_tokens_used": state.get("total_tokens_used", 0) + tokens_rerank,
            "completed_nodes": [*state.get("completed_nodes", []), "data_retriever"],
        }
    except Exception as e:
        logger.error(f"data_retriever error: {e}")
        return {
            **state,
            "catalog_chunks":    [],
            "review_chunks":     [],
            "pricing_chunks":    [],
            "competitor_chunks": [],
            "order_chunks":      [],
            "customer_chunks":   [],
            "error": str(e),
        }
