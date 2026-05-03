"""F3 训练计划模型: 跟读/背诵模式 + 艾宾浩斯间隔复习排程"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (BigInteger, String, SmallInteger, Integer, Date,
                        DateTime, Numeric, Text, JSON, ForeignKey, Index, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class TrainingPlan(Base):
    """
    一个训练计划对应一个述标任务的练习排程。
    每个 (user_id, pitch_task_id) 只有一份有效计划。
    """
    __tablename__ = "training_plan"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pitch_task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pitch_task.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("pitch_plan.id", ondelete="SET NULL"), nullable=True
    )

    first_practice_date: Mapped[date | None] = mapped_column(Date)
    bid_date: Mapped[date | None] = mapped_column(Date)
    # Serialised as ISO date strings: ["2025-06-01", "2025-06-02", ...]
    schedule_dates: Mapped[list | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    sessions: Mapped[list["TrainingSession"]] = relationship(
        "TrainingSession", back_populates="plan", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_training_plan_user_task", "user_id", "pitch_task_id"),
        Index("idx_training_plan_tenant", "tenant_id"),
    )


class TrainingSession(Base):
    """
    一次练习记录。每次练完一个模式（跟读/背诵）保存一行。
    """
    __tablename__ = "training_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("training_plan.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pitch_task_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # mode: "follow" (跟读) | "recite" (背诵)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)

    audio_url: Mapped[str | None] = mapped_column(String(512))
    transcript: Mapped[str | None] = mapped_column(Text)

    # Scores (0-100)
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    # follow: content_alignment, rate_match, emphasis_hits
    # recite: coverage_rate, order_accuracy, naturalness
    dimension_scores: Mapped[dict | None] = mapped_column(JSON)
    feedback: Mapped[list | None] = mapped_column(JSON)   # list of tip strings

    practice_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    plan: Mapped["TrainingPlan"] = relationship("TrainingPlan", back_populates="sessions")

    __table_args__ = (
        Index("idx_ts_plan", "plan_id"),
        Index("idx_ts_user_date", "user_id", "practice_date"),
    )
