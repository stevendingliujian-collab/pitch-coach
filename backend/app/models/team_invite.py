"""TeamInvite model — invite-link-based team join flow."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class TeamInvite(Base):
    __tablename__ = "team_invite"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    invite_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grant_role: Mapped[str] = mapped_column(String(32), nullable=False, default="presenter")
    note: Mapped[str | None] = mapped_column(String(256))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_invite_tenant", "tenant_id"),
    )

    @property
    def is_valid(self) -> bool:
        if self.used_count >= self.max_uses:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
