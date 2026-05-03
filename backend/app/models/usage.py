"""
Usage metering models for free-tier quota enforcement.
"""
from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, DateTime, JSON, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class UsageMeter(Base):
    """Monthly running totals per user — updated atomically on each feature use."""
    __tablename__ = "usage_meter"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)  # "2026-05"

    ppt_uploads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rehearsals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    narration_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    knowledge_docs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "year_month", name="uk_user_month"),
    )


class UsageEvent(Base):
    """Immutable audit log — one row per quota-consuming action."""
    __tablename__ = "usage_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    feature: Mapped[str] = mapped_column(String(64), nullable=False)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_usage_event_user_month", "user_id", "year_month"),
    )
