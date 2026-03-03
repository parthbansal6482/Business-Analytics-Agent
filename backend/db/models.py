import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .session import Base


def now_utc():
    return datetime.now(timezone.utc)


class UploadRecord(Base):
    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    data_type: Mapped[str] = mapped_column(String, nullable=False)  # catalog/reviews/pricing/competitors
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String, default="manual")   # manual / shopify
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ResearchSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String, default="quick")
    report_json: Mapped[str] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class TokenLog(Base):
    __tablename__ = "token_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.session_id"), nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ShopifyConnection(Base):
    __tablename__ = "shopify_connections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    shop_domain: Mapped[str] = mapped_column(String, nullable=False)
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    products_synced: Mapped[int] = mapped_column(Integer, default=0)
    orders_synced: Mapped[int] = mapped_column(Integer, default=0)
    reviews_synced: Mapped[int] = mapped_column(Integer, default=0)
    last_sync: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    preferred_kpis: Mapped[str] = mapped_column(Text, default="[]")       # JSON list
    marketplaces: Mapped[str] = mapped_column(Text, default="[]")         # JSON list
    categories: Mapped[str] = mapped_column(Text, default="[]")           # JSON list
    analysis_style: Mapped[str] = mapped_column(String, default="growth-focused")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
