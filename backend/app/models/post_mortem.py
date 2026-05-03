from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    BigInteger, String, SmallInteger, Integer, DateTime, Numeric,
    Text, JSON, Boolean, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class PostMortem(Base):
    """述标复盘报告 — 对真实述标会议录音进行 AI 分析"""
    __tablename__ = "post_mortem"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pitch_task_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    recording_url: Mapped[str | None] = mapped_column(String(512))
    recording_duration: Mapped[int | None] = mapped_column(Integer)  # seconds

    # pending | processing | completed | failed
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")

    # [{speaker: "us"|"evaluator_1"|..., start: float, end: float, text: str}]
    diarization: Mapped[list | None] = mapped_column(JSON)

    # [{id, category, question, start_time, answer_text, answer_quality, notes}]
    evaluator_questions: Mapped[list | None] = mapped_column(JSON)

    our_talk_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    evaluator_count: Mapped[int | None] = mapped_column(Integer)
    question_count: Mapped[int | None] = mapped_column(Integer)

    # {tech: N, business: N, user: N, compliance: N, other: N}
    question_categories: Mapped[dict | None] = mapped_column(JSON)

    prediction_hit_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # [{question_id, score, feedback, reference_from_kb}]
    answer_assessments: Mapped[list | None] = mapped_column(JSON)

    followup_draft: Mapped[str | None] = mapped_column(Text)

    # [{time, speaker, highlight_type, text}]
    key_moments: Mapped[list | None] = mapped_column(JSON)

    # {strengths: [...], weaknesses: [...], recommendations: [...]}
    insights: Mapped[dict | None] = mapped_column(JSON)

    task_id: Mapped[str | None] = mapped_column(String(64))
    error_msg: Mapped[str | None] = mapped_column(String(512))

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_pm_tenant", "tenant_id"),
        Index("idx_pm_task", "pitch_task_id"),
        Index("idx_pm_status", "status"),
    )


class ApiKey(Base):
    """Open API 密钥"""
    __tablename__ = "api_key"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_apikey_tenant", "tenant_id"),
    )


class ApiUsage(Base):
    """Open API 用量计量"""
    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    api_key_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    endpoint: Mapped[str] = mapped_column(String(128), nullable=False)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    status_code: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    response_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_apiusage_tenant", "tenant_id"),
        Index("idx_apiusage_key", "api_key_id"),
    )
