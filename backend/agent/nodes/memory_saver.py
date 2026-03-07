"""
Memory Saver: persists session summary to Qdrant and updates user preferences in Redis.
"""

import json
import logging
import os

import redis as sync_redis

from agent.state import AgentState
from data.embedder import embed_one
from memory.qdrant_store import upsert_chunks
from utils.sse import publish_step

logger = logging.getLogger(__name__)

_r = sync_redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)


def memory_saver(state: AgentState) -> AgentState:
    try:
        session_id = state["session_id"]
        user_id = state["user_id"]
        report = state.get("report", {})

        # Create a clean session summary for future memory retrieval.
        # Important: do NOT use "Query: ... Findings: ..." format — that gets
        # regurgitated verbatim in future answers as "Prior context considered".
        exec_summary = report.get('executive_summary', '')[:200]
        summary = (
            f"Previous analysis on '{state['query'][:80]}': "
            f"{exec_summary}. "
            f"Confidence: {report.get('confidence_score', 0)}."
        )

        # Embed and upsert to ecomm_user_memory
        vec = embed_one(summary)
        upsert_chunks(
            "ecomm_user_memory",
            [{"text": summary, "session_id": session_id, "query": state["query"]}],
            [vec],
            user_id,
        )

        # Persist/update preferences in Redis
        prefs = state.get("user_preferences", {})
        if prefs:
            _r.set(f"prefs:{user_id}", json.dumps(prefs), ex=86400 * 30)

        # Cache full report in Redis for quick retrieval (TTL 7 days)
        if report:
            _r.set(f"report:{session_id}", json.dumps(report), ex=86400 * 7)

        publish_step(session_id, "memory_save", "done", "Memory saved")

        return {
            **state,
            "completed_nodes": [*state.get("completed_nodes", []), "memory_saver"],
        }
    except Exception as e:
        logger.error(f"memory_saver error: {e}")
        # Non-fatal — report already generated
        return {**state, "error": None}
