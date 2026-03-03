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

        publish_step(session_id, "memory", "done", "Preferences loaded")

        return {
            **state,
            "user_preferences": user_preferences,
            "past_analyses": past_analyses,
            "completed_nodes": [*state.get("completed_nodes", []), "memory_loader"],
        }
    except Exception as e:
        logger.error(f"memory_loader error: {e}")
        return {**state, "user_preferences": {}, "past_analyses": [], "error": None}
