from datetime import datetime
from decimal import Decimal
from sqlalchemy import (BigInteger, String, SmallInteger, Integer, DateTime,
                        Numeric, Text, JSON, ForeignKey, Index, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

# Sentinel audio_url for practice results logged via the Open API (MCP tools).
# These rows carry externally reported scores, not platform-verified rehearsals,
# and must be excluded from dashboards / leaderboards / ROI aggregations.
EXTERNAL_MCP_AUDIO_URL = "external://mcp_log"

# Rehearsal.status values.
#   0=录制中 1=转录中 2=评分中 3=已评分 4=已提交审核 5=已通过认证
#   6=需改进（经理驳回认证）  7=评分失败（转录/评分环节出错，无有效分数）
# Status 7 is distinct from 6: a manager-rejected rehearsal (6) has a real
# score, whereas a failed one (7) has none and must not pollute aggregations.
STATUS_SCORED = 3
STATUS_NEEDS_IMPROVEMENT = 6
STATUS_FAILED = 7


class Rehearsal(Base):
    __tablename__ = "rehearsal"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pitch_task_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    plan_id: Mapped[int | None] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    audio_url: Mapped[str] = mapped_column(String(512), nullable=False)
    audio_duration: Mapped[int] = mapped_column(Integer, nullable=False)
    video_url: Mapped[str | None] = mapped_column(String(512))

    page_timings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    transcript_json: Mapped[list | None] = mapped_column(JSON)

    # AI scoring
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    dimension_scores: Mapped[dict | None] = mapped_column(JSON)
    page_scores: Mapped[list | None] = mapped_column(JSON)
    improvement_tips: Mapped[list | None] = mapped_column(JSON)
    filler_word_count: Mapped[int | None] = mapped_column(Integer)
    filler_word_detail: Mapped[list | None] = mapped_column(JSON)

    # See status constants above: 0..7
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    # Populated when status=7 (scoring failed): user-facing reason for the failure.
    error_msg: Mapped[str | None] = mapped_column(String(512))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    comments: Mapped[list["ReviewComment"]] = relationship("ReviewComment", back_populates="rehearsal")

    __table_args__ = (
        Index("idx_tenant_task_rehearsal", "tenant_id", "pitch_task_id"),
        Index("idx_user_rehearsal", "tenant_id", "user_id"),
        Index("idx_status_rehearsal", "tenant_id", "status"),
    )


# Avoid circular import — ReviewComment is in review.py
from app.models.review import ReviewComment  # noqa: E402
