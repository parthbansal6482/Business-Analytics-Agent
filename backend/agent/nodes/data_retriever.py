"""
Data Retriever: embeds the query and searches all 4 Qdrant collections.
"""

import logging
from agent.state import AgentState
from data.embedder import embed_one
from memory.qdrant_store import search
from utils.sse import publish_step

logger = logging.getLogger(__name__)


def data_retriever(state: AgentState) -> AgentState:
    try:
        query = state["query"]
        user_id = state["user_id"]
        session_id = state["session_id"]
        mode = state.get("mode", "quick")

        # Embed once, reuse across all searches
        query_vec = embed_one(query)
        top_k = 15 if mode == "deep" else 8

        catalog_res  = search("ecomm_catalog",     query_vec, user_id, top_k=top_k)
        review_res   = search("ecomm_reviews",     query_vec, user_id, top_k=top_k)
        pricing_res  = search("ecomm_pricing",     query_vec, user_id, top_k=top_k)
        competitor_res = search("ecomm_competitors", query_vec, user_id, top_k=top_k)
        order_res    = search("ecomm_orders",      query_vec, user_id, top_k=top_k)
        customer_res = search("ecomm_customers",   query_vec, user_id, top_k=top_k)

        catalog_chunks  = [r["text"] for r in catalog_res if r.get("text")]
        review_chunks   = [r["text"] for r in review_res if r.get("text")]
        pricing_chunks  = [r["text"] for r in pricing_res if r.get("text")]
        competitor_chunks = [r["text"] for r in competitor_res if r.get("text")]
        order_chunks    = [r["text"] for r in order_res if r.get("text")]
        customer_chunks = [r["text"] for r in customer_res if r.get("text")]

        logger.info(
            f"Retrieved: catalog={len(catalog_chunks)} reviews={len(review_chunks)} "
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
            len(catalog_chunks)
            + len(review_chunks)
            + len(pricing_chunks)
            + len(competitor_chunks)
            + len(order_chunks)
            + len(customer_chunks)
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
            "catalog_chunks": catalog_chunks,
            "review_chunks": review_chunks,
            "pricing_chunks": pricing_chunks,
            "competitor_chunks": competitor_chunks,
            "order_chunks": order_chunks,
            "customer_chunks": customer_chunks,
            "completed_nodes": [*state.get("completed_nodes", []), "data_retriever"],
        }
    except Exception as e:
        logger.error(f"data_retriever error: {e}")
        return {
            **state,
            "catalog_chunks": [],
            "review_chunks": [],
            "pricing_chunks": [],
            "competitor_chunks": [],
            "order_chunks": [],
            "customer_chunks": [],
            "error": str(e),
        }
