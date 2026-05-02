from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(64))
    plan_type: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_rehearsals_month: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    integration_type: Mapped[str | None] = mapped_column(String(32))
    integration_config: Mapped[dict | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
