"""
User memory read/write: PostgreSQL preferences + Redis cache.
"""

import json
import logging
import os
from datetime import datetime, timezone

import redis as sync_redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserPreference
from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

_r = sync_redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)


async def get_preferences(user_id: str) -> dict:
    """Load user preferences from PG (via Redis cache)."""
    # Try Redis first
    cached = _r.get(f"prefs:{user_id}")
    if cached:
        return json.loads(cached)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()

        if not pref:
            return {
                "preferred_kpis": [],
                "marketplaces": [],
                "categories": [],
                "analysis_style": "growth-focused",
            }

        data = {
            "preferred_kpis": json.loads(pref.preferred_kpis or "[]"),
            "marketplaces": json.loads(pref.marketplaces or "[]"),
            "categories": json.loads(pref.categories or "[]"),
            "analysis_style": pref.analysis_style,
        }

        # Populate Redis cache
        _r.set(f"prefs:{user_id}", json.dumps(data), ex=86400 * 7)
        return data


async def save_preferences(user_id: str, updates: dict) -> dict:
    """Save preference updates to PG and invalidate cache."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()

        if not pref:
            pref = UserPreference(user_id=user_id)
            db.add(pref)

        if "preferred_kpis" in updates:
            pref.preferred_kpis = json.dumps(updates["preferred_kpis"])
        if "marketplaces" in updates:
            pref.marketplaces = json.dumps(updates["marketplaces"])
        if "categories" in updates:
            pref.categories = json.dumps(updates["categories"])
        if "analysis_style" in updates:
            pref.analysis_style = updates["analysis_style"]
        pref.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(pref)

    # Invalidate Redis
    _r.delete(f"prefs:{user_id}")

    return await get_preferences(user_id)


async def delete_user_memory(user_id: str) -> None:
    """Wipe all user memory from Qdrant + Redis."""
    from memory.qdrant_store import delete_by_user, COLLECTIONS
    for coll in COLLECTIONS:
        delete_by_user(coll, user_id)
    _r.delete(f"prefs:{user_id}")
    logger.info(f"Wiped all memory for user {user_id}")
