"""
SSE helper utilities for streaming agent progress to frontend.
Each node publishes a step event; this module formats + publishes to Redis (sync).
"""

import json
import os
import time
import redis as sync_redis

_redis_client = None


def get_redis() -> sync_redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = sync_redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True,
        )
    return _redis_client


def publish_step(session_id: str, step: str, status: str, label: str = "") -> None:
    """Publish an SSE progress event for a given session."""
    r = get_redis()
    payload = json.dumps({"step": step, "status": status, "label": label})
    r.publish(f"progress:{session_id}", payload)
    # Small delay to ensure event order
    time.sleep(0.05)


def format_sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"
