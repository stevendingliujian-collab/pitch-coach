from datetime import datetime
from sqlalchemy import BigInteger, String, Boolean, DateTime, JSON, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AbTest(Base):
    __tablename__ = "ab_test"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(512))
    variants: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    weights: Mapped[list | None] = mapped_column(JSON)           # e.g. [50, 50]
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime)
    end_date: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class AbTestAssignment(Base):
    __tablename__ = "ab_test_assignment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    test_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    variant: Mapped[str] = mapped_column(String(64), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_ab_assign_user_test", "user_id", "test_name", unique=True),
        Index("ix_ab_assign_tenant_test", "tenant_id", "test_name"),
    )


class AbTestEvent(Base):
    __tablename__ = "ab_test_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    test_name: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    variant: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_ab_event_test_variant", "test_name", "variant"),
    )
