from datetime import datetime
from sqlalchemy import (BigInteger, String, SmallInteger, DateTime, Numeric,
                        Text, JSON, Boolean, ForeignKey, Index, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ReviewComment(Base):
    __tablename__ = "review_comment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rehearsal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("rehearsal.id", ondelete="CASCADE"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    timestamp_sec: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_highlight: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mentioned_users: Mapped[list | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    rehearsal: Mapped["Rehearsal"] = relationship("Rehearsal", back_populates="comments")

    __table_args__ = (
        Index("idx_rehearsal_comment", "rehearsal_id"),
    )


class Certification(Base):
    __tablename__ = "certification"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pitch_task_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reviewer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rehearsal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("rehearsal.id"), nullable=False)

    # 0=待审核 1=通过 2=拒绝
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    review_comment: Mapped[str | None] = mapped_column(Text)
    certified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "pitch_task_id", "user_id", name="uk_task_user_cert"),
    )


# late import to avoid circular ref
from app.models.rehearsal import Rehearsal  # noqa: E402
