import logging
from sqlalchemy import text

from .session import engine, Base
from .models import UploadRecord, ResearchSession, TokenLog, ShopifyConnection, UserPreference

logger = logging.getLogger(__name__)


async def _ensure_shopify_columns():
    """Best-effort schema backfill for environments without migrations."""
    statements = [
        "ALTER TABLE shopify_connections ADD COLUMN IF NOT EXISTS products_synced INTEGER DEFAULT 0 NOT NULL",
        "ALTER TABLE shopify_connections ADD COLUMN IF NOT EXISTS orders_synced INTEGER DEFAULT 0 NOT NULL",
        "ALTER TABLE shopify_connections ADD COLUMN IF NOT EXISTS reviews_synced INTEGER DEFAULT 0 NOT NULL",
        "ALTER TABLE shopify_connections ADD COLUMN IF NOT EXISTS last_sync TIMESTAMPTZ NULL",
        "ALTER TABLE shopify_connections ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL",
    ]
    async with engine.begin() as conn:
        for stmt in statements:
            try:
                await conn.execute(text(stmt))
            except Exception:
                # If table doesn't exist yet, create_all will handle it.
                logger.debug("Skipping schema patch statement: %s", stmt, exc_info=True)


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _ensure_shopify_columns()


__all__ = ["init_db", "UploadRecord", "ResearchSession", "TokenLog", "ShopifyConnection", "UserPreference"]
