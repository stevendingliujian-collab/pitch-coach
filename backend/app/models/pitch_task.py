from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import BigInteger, String, SmallInteger, DateTime, Date, Numeric, Text, JSON, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class PitchTask(Base):
    """述标任务 — 独立模式显示为"项目"，CRM嵌入模式对应商机的影子记录"""
    __tablename__ = "pitch_task"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(128))
    customer_industry: Mapped[str | None] = mapped_column(String(64))
    budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))

    bid_date: Mapped[date | None] = mapped_column(Date)
    bid_time_limit: Mapped[int | None] = mapped_column(SmallInteger)  # minutes
    bid_requirements: Mapped[str | None] = mapped_column(Text)
    competitor_info: Mapped[list | None] = mapped_column(JSON)

    result: Mapped[int | None] = mapped_column(SmallInteger)  # 1=中标 2=未中标 3=弃标 4=流标

    # CRM integration
    external_id: Mapped[str | None] = mapped_column(String(128))
    external_type: Mapped[str | None] = mapped_column(String(32))

    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    member_ids: Mapped[list | None] = mapped_column(JSON)

    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "external_type", "external_id", name="uk_external"),
        Index("idx_tenant_status", "tenant_id", "status"),
        Index("idx_bid_date", "tenant_id", "bid_date"),
    )
