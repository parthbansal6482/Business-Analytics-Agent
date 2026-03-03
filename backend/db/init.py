from .session import engine, Base
from .models import UploadRecord, ResearchSession, TokenLog, ShopifyConnection, UserPreference


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


__all__ = ["init_db", "UploadRecord", "ResearchSession", "TokenLog", "ShopifyConnection", "UserPreference"]
