"""Models for conversion triggers, trigger events, and analytics events."""
from datetime import datetime
from sqlalchemy import (BigInteger, String, Integer, Boolean, DateTime,
                        JSON, Index, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class UpgradeTrigger(Base):
    """Tracks which upgrade-prompt triggers have been shown to each user."""
    __tablename__ = "upgrade_trigger"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    trigger_id: Mapped[str] = mapped_column(String(16), nullable=False)
    show_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_shows: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    converted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_shown_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_upgrade_trigger_user", "user_id", "trigger_id", unique=True),
        Index("idx_upgrade_trigger_tenant", "tenant_id"),
    )


class TriggerEvent(Base):
    """Immutable log of trigger show / dismiss / convert events."""
    __tablename__ = "trigger_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    trigger_id: Mapped[str] = mapped_column(String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)  # shown/dismissed/converted
    meta: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_trigger_event_user", "user_id", "trigger_id"),
    )


class AnalyticsEvent(Base):
    """Lightweight funnel events (registration → activation → rehearsal → payment)."""
    __tablename__ = "analytics_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_name: Mapped[str] = mapped_column(String(64), nullable=False)
    properties: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_analytics_event_user", "user_id", "event_name"),
        Index("idx_analytics_event_tenant_time", "tenant_id", "created_at"),
    )
