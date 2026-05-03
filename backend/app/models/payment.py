from datetime import datetime
from decimal import Decimal
from sqlalchemy import (BigInteger, String, Numeric, DateTime, Index, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 'wechat_pay' | 'alipay' | 'bank_transfer' | 'trial' | 'manual'
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    # 'pending' | 'completed' | 'failed' | 'refunded'
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    plan_type: Mapped[str] = mapped_column(String(32), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(16), nullable=False, default="monthly")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    description: Mapped[str | None] = mapped_column(String(255))
    transaction_id: Mapped[str | None] = mapped_column(String(128))
    invoice_no: Mapped[str | None] = mapped_column(String(64), unique=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime)
    period_end: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                  server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_payment_tenant", "tenant_id"),
        Index("idx_payment_status", "status"),
    )
