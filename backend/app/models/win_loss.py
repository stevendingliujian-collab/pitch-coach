from datetime import datetime
from decimal import Decimal
from sqlalchemy import (BigInteger, String, SmallInteger, Integer, DateTime,
                        Numeric, Text, JSON, UniqueConstraint, Index, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class WinLossRecord(Base):
    __tablename__ = "win_loss_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pitch_task_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # 1=中标 2=未中标 3=弃标 4=流标
    result: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    bid_score_total: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    bid_score_business: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    bid_score_technical: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    bid_score_pitch: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    loss_reason_code: Mapped[str | None] = mapped_column(String(32))
    loss_reason_detail: Mapped[str | None] = mapped_column(Text)

    best_rehearsal_id: Mapped[int | None] = mapped_column(BigInteger)
    best_rehearsal_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    rehearsal_count: Mapped[int | None] = mapped_column(Integer)

    competitor_names: Mapped[list | None] = mapped_column(JSON)
    winning_competitor: Mapped[str | None] = mapped_column(String(128))

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "pitch_task_id", name="uk_task_win_loss"),
        Index("idx_result", "tenant_id", "result"),
    )
