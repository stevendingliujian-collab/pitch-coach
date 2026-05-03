from datetime import datetime
from decimal import Decimal
from sqlalchemy import (BigInteger, String, Text, Numeric, JSON, Boolean,
                        DateTime, ForeignKey, Index, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ScoringRubric(Base):
    __tablename__ = "scoring_rubric"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # 'manual' | 'pdf_parsed' | 'template'
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    source_file_url: Mapped[str | None] = mapped_column(String(512))
    # [{id, category, item, max_score, weight, description}]
    items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    total_max_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    industry: Mapped[str | None] = mapped_column(String(64))
    template_type: Mapped[str | None] = mapped_column(String(64))
    is_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                  server_default=func.now(), onupdate=func.now())

    rubric_scores: Mapped[list["RubricScore"]] = relationship(
        "RubricScore", back_populates="rubric", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_rubric_tenant", "tenant_id"),
        Index("idx_rubric_template", "is_template"),
    )


class RubricScore(Base):
    __tablename__ = "rubric_score"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rubric_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("scoring_rubric.id", ondelete="CASCADE"), nullable=False)
    rehearsal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("rehearsal.id", ondelete="CASCADE"), nullable=False)
    # [{item_id, score, coverage, note, suggest_page}]
    scores: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    # 0.0 – 1.0
    coverage_percent: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    # [{item_id, covered, evidence}]
    coverage_detail: Mapped[list | None] = mapped_column(JSON)
    # [{item_id, suggestion}]
    improvement_suggestions: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    rubric: Mapped["ScoringRubric"] = relationship("ScoringRubric", back_populates="rubric_scores")

    __table_args__ = (
        Index("idx_rubric_score_rehearsal", "rehearsal_id"),
        Index("idx_rubric_score_rubric", "rubric_id"),
        Index("uk_rubric_score_rubric_rehearsal", "rubric_id", "rehearsal_id", unique=True),
    )
