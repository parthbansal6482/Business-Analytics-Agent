"""
Data Retriever: embeds the query and searches all Qdrant collections.
Deep Mode uses DEEP_MODE_TOP_K chunks and LLM-based review reranking.
Quick Mode uses QUICK_MODE_TOP_K chunks only.
All config values are read from environment variables.
"""

import os
import json
import logging
import re

from agent.state import AgentState
from data.embedder import embed_one
from memory.qdrant_store import search
from utils.sse import publish_step
from utils.llm import call_llm_with_retry

logger = logging.getLogger(__name__)

QUICK_TOP_K  = int(os.getenv("QUICK_MODE_TOP_K", "10"))
DEEP_TOP_K   = int(os.getenv("DEEP_MODE_TOP_K",  "30"))
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K",     "15"))


def rerank_reviews(query: str, review_chunks: list[str]) -> list[str]:
    """LLM-based review reranking — only used in Deep Mode."""
    if len(review_chunks) <= RERANK_TOP_K:
        return review_chunks

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
                return reranked
    except Exception as e:
        logger.warning(f"Review reranking failed (using top-K fallback): {e}")

    return review_chunks[:RERANK_TOP_K]


def data_retriever(state: AgentState) -> AgentState:
    try:
        query      = state["query"]
        user_id    = state["user_id"]
        session_id = state["session_id"]
        mode       = state.get("mode", "quick")

        top_k = DEEP_TOP_K if mode == "deep" else QUICK_TOP_K

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

        # Deep Mode: LLM-based review reranking for higher signal quality
        if mode == "deep" and review_chunks:
            review_chunks = rerank_reviews(query, review_chunks)

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
                "or competitor data first, or connect your Shopify store."
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
