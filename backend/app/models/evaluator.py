from datetime import datetime
from decimal import Decimal
from sqlalchemy import (BigInteger, String, Text, SmallInteger, Numeric,
                        Boolean, JSON, DateTime, ForeignKey, Index, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class EvaluatorPersona(Base):
    __tablename__ = "evaluator_persona"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 'system' = global preset, 'custom' = tenant-specific
    persona_type: Mapped[str] = mapped_column(String(32), nullable=False, default="custom")
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_emoji: Mapped[str | None] = mapped_column(String(8), default="🧑‍⚖️")
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    focus_areas: Mapped[list | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    sessions: Mapped[list["QASession"]] = relationship("QASession", back_populates="evaluator")

    __table_args__ = (
        Index("idx_evaluator_tenant", "tenant_id"),
        Index("idx_evaluator_type", "persona_type"),
    )


class QASession(Base):
    __tablename__ = "qa_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pitch_task_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    evaluator_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("evaluator_persona.id", ondelete="SET NULL")
    )
    # 'single' | 'panel'
    session_type: Mapped[str] = mapped_column(String(16), nullable=False, default="single")
    # [{role: 'evaluator'|'user', content, audio_url?, score?}]
    messages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # 0=init 1=in_progress 2=completed
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    feedback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                  server_default=func.now(), onupdate=func.now())

    evaluator: Mapped["EvaluatorPersona | None"] = relationship("EvaluatorPersona", back_populates="sessions")

    __table_args__ = (
        Index("idx_qa_tenant_task", "tenant_id", "pitch_task_id"),
        Index("idx_qa_user", "user_id"),
    )
