"""
Daily Micro-Practice models (F9).

Tables:
  daily_practice_item  — pre-built practice content (system templates)
  daily_practice_log   — user practice session records (streak tracking)
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (BigInteger, String, SmallInteger, Integer, Date,
                        DateTime, Numeric, Text, JSON, Index, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class DailyPracticeItem(Base):
    """
    Practice content pool — rotated by weekday.
    System pre-built; can later be extended with knowledge-base items.
    """
    __tablename__ = "daily_practice_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Content
    practice_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="intro/case/term/qa/competitive/review"
    )
    weekday: Mapped[int | None] = mapped_column(
        SmallInteger,
        comment="0=Mon...6=Sun; NULL=universal"
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False, comment="用户看到的练习说明")
    target_duration_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    # Scoring hints
    key_points: Mapped[list | None] = mapped_column(
        JSON, comment="关键词列表，用于关键词命中率评分"
    )
    reference_answer: Mapped[str | None] = mapped_column(Text, comment="参考答案（显示给用户）")

    # Source
    industry: Mapped[str | None] = mapped_column(String(64), comment="适用行业，NULL=通用")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="system",
                                         comment="system/knowledge_base")
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class DailyPracticeLog(Base):
    """
    User's daily practice session record.
    One record per user per day (replace if redo within same day).
    """
    __tablename__ = "daily_practice_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    practice_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Recording
    audio_url: Mapped[str | None] = mapped_column(String(512))
    audio_duration_sec: Mapped[int | None] = mapped_column(Integer)
    transcript: Mapped[str | None] = mapped_column(Text)

    # Scoring (rule-based lightweight engine)
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    completion_ok: Mapped[bool | None] = mapped_column(comment="是否讲完了要点")
    timing_sec: Mapped[int | None] = mapped_column(Integer, comment="实际时长(秒)")
    filler_count: Mapped[int | None] = mapped_column(Integer)
    keyword_hit_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3), comment="关键词命中率 0~1"
    )
    feedback: Mapped[dict | None] = mapped_column(JSON, comment="改进提示")

    # Status: 0=录制中 1=已完成
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_dp_user_date", "user_id", "practice_date"),
        Index("idx_dp_tenant", "tenant_id"),
    )


class UserStreak(Base):
    """
    Tracks each user's current streak and personal best.
    One row per user; upserted when practice is completed.
    """
    __tablename__ = "user_streak"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_practice_date: Mapped[date | None] = mapped_column(Date)

    total_practices: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_streak_tenant", "tenant_id"),
    )
