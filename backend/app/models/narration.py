from datetime import datetime
from sqlalchemy import BigInteger, String, SmallInteger, Integer, DateTime, Text, JSON, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class DemoNarration(Base):
    """AI 示范讲解记录：逐页 TTS 合成后拼接的完整讲解音频。"""
    __tablename__ = "demo_narration"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pitch_plan.id", ondelete="CASCADE"), nullable=False
    )

    # Generation config
    voice_id: Mapped[str] = mapped_column(String(128), nullable=False)
    voice_name: Mapped[str | None] = mapped_column(String(64))   # display name
    speed: Mapped[float] = mapped_column(nullable=False, server_default="1.0")

    # Results
    # [{page_number, script, audio_url, duration_sec}]
    page_audios: Mapped[list | None] = mapped_column(JSON)
    total_audio_url: Mapped[str | None] = mapped_column(String(512))  # merged MP3 key
    total_duration_sec: Mapped[int | None] = mapped_column(Integer)

    # 0=pending 1=generating_scripts 2=synthesizing 3=merging 4=ready 5=error
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    error_msg: Mapped[str | None] = mapped_column(Text)

    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_narration_plan", "plan_id"),
        Index("idx_narration_tenant", "tenant_id"),
    )
