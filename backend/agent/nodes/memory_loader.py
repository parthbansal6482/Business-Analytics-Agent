"""
Memory Loader: reads user preferences and past session summaries from Qdrant.
"""

import json
import logging
import os

import redis as sync_redis

from agent.state import AgentState
from data.embedder import embed_one
from memory.qdrant_store import search
from utils.sse import publish_step

logger = logging.getLogger(__name__)

_r = sync_redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)


def memory_loader(state: AgentState) -> AgentState:
    try:
        user_id = state["user_id"]
        session_id = state["session_id"]

        # Load preferences from Redis (fast path)
        prefs_raw = _r.get(f"prefs:{user_id}")
        if prefs_raw:
            user_preferences = json.loads(prefs_raw)
        else:
            user_preferences = {
                "preferred_kpis": [],
                "marketplaces": [],
                "categories_of_interest": [],
                "analysis_style": "growth-focused",
            }

        # Load past session summaries from Qdrant user memory
        query_vec = embed_one(state["query"])
        past_results = search("ecomm_user_memory", query_vec, user_id, top_k=3)
        past_analyses = [r["text"] for r in past_results if r.get("text")]

        # Load real database counts to prevent LLM hallucination based on truncated chunks
        import os
        import psycopg2

        products_synced = 0
        orders_synced = 0
        customers_synced = 0

        try:
            # Use sync psycopg2 — safe from worker threads (asyncpg won't work here)
            raw_url = os.getenv("POSTGRES_URL", "").replace("postgresql+asyncpg://", "postgresql://")
            with psycopg2.connect(raw_url) as pg_conn:
                with pg_conn.cursor() as cur:
                    cur.execute(
                        "SELECT products_synced, orders_synced, reviews_synced FROM shopify_connections WHERE user_id = %s LIMIT 1",
                        (user_id,)
                    )
                    row = cur.fetchone()
                    if row:
                        products_synced = row[0] or 0
                        orders_synced = row[1] or 0
                        customers_synced = row[2] or 0

                    # Include manual-upload counts so "Actual Database Metrics" are not zero for non-Shopify users.
                    cur.execute(
                        "SELECT data_type, COALESCE(SUM(row_count), 0) FROM uploads WHERE user_id = %s GROUP BY data_type",
                        (user_id,)
                    )
                    upload_counts = {dtype: int(cnt or 0) for dtype, cnt in cur.fetchall()}
                    products_synced = max(products_synced, upload_counts.get("catalog", 0))
                    orders_synced = max(orders_synced, upload_counts.get("orders", 0))
                    # This key is used as a third high-level count; map manual review rows when customer rows aren't present.
                    customers_synced = max(
                        customers_synced,
                        upload_counts.get("customers", 0),
                        upload_counts.get("reviews", 0),
                    )


        except Exception as db_err:
            logger.error(f"Failed to fetch DB counts in memory loader: {db_err}")

        publish_step(session_id, "memory", "done", "Preferences and real counts loaded")

        return {
            **state,
            "user_preferences": user_preferences,
            "past_analyses": past_analyses,
            "total_products_synced": products_synced,
            "total_orders_synced": orders_synced,
            "total_customers_synced": customers_synced,
            "completed_nodes": [*state.get("completed_nodes", []), "memory_loader"],
        }
    except Exception as e:
        logger.error(f"memory_loader error: {e}")
        return {
            **state,
            "user_preferences": {},
            "past_analyses": [],
            "total_products_synced": 0,
            "total_orders_synced": 0,
            "total_customers_synced": 0,
            "error": None
        }
