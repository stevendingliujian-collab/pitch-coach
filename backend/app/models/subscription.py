"""Subscription model — tracks trial / paid plan status per tenant."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Subscription(Base):
    __tablename__ = "subscription"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # status: free | trial | active | cancelled | expired
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    plan_type: Mapped[str] = mapped_column(String(32), nullable=False, default="free")

    trial_starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uk_subscription_tenant"),
        Index("idx_subscription_tenant", "tenant_id"),
        Index("idx_subscription_status", "status"),
    )

    @property
    def is_active(self) -> bool:
        """True if the tenant has professional features available right now."""
        now = datetime.utcnow()
        if self.status == "active":
            return self.expires_at is None or now < self.expires_at
        if self.status == "trial":
            return self.trial_ends_at is not None and now < self.trial_ends_at
        return False

    @property
    def effective_plan(self) -> str:
        """Return 'pro' when active/trial, else 'free'."""
        return "pro" if self.is_active else "free"

    @property
    def trial_days_left(self) -> int | None:
        """Days remaining in trial, or None."""
        if self.status == "trial" and self.trial_ends_at:
            delta = self.trial_ends_at - datetime.utcnow()
            return max(0, delta.days)
        return None
