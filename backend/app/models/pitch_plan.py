from datetime import datetime
from decimal import Decimal
from sqlalchemy import (BigInteger, String, SmallInteger, Integer, DateTime,
                        Numeric, Text, JSON, Boolean, Index, ForeignKey, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class PitchPlan(Base):
    __tablename__ = "pitch_plan"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pitch_task_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    ppt_file_id: Mapped[str] = mapped_column(String(128), nullable=False)  # OSS object key
    ppt_file_name: Mapped[str] = mapped_column(String(256), nullable=False)
    ppt_page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Context
    customer_name: Mapped[str | None] = mapped_column(String(128))
    customer_industry: Mapped[str | None] = mapped_column(String(64))
    project_budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    bid_requirements: Mapped[str | None] = mapped_column(Text)
    bid_time_limit: Mapped[int | None] = mapped_column(Integer)  # minutes
    competitor_info: Mapped[list | None] = mapped_column(JSON)

    # AI-generated plan
    global_strategy: Mapped[str | None] = mapped_column(Text)
    total_duration_sec: Mapped[int | None] = mapped_column(Integer)
    predicted_questions: Mapped[list | None] = mapped_column(JSON)
    competitive_differentiation: Mapped[list | None] = mapped_column(JSON)
    opening_templates: Mapped[list | None] = mapped_column(JSON)
    closing_templates: Mapped[list | None] = mapped_column(JSON)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 0=生成中 1=已生成 2=已人工编辑 3=已归档
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    pages: Mapped[list["PlanPage"]] = relationship("PlanPage", back_populates="plan", order_by="PlanPage.page_number")

    __table_args__ = (
        Index("idx_tenant_task_plan", "tenant_id", "pitch_task_id"),
    )


class PlanPage(Base):
    __tablename__ = "plan_page"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pitch_plan.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)

    page_title: Mapped[str | None] = mapped_column(String(256))
    page_content_summary: Mapped[str | None] = mapped_column(Text)
    page_thumbnail_url: Mapped[str | None] = mapped_column(String(512))

    # 1=快速带过 2=重要 3=核心
    importance_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    talking_points: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    suggested_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=60)  # seconds
    emphasis_marks: Mapped[list | None] = mapped_column(JSON)
    bid_req_mapping: Mapped[list | None] = mapped_column(JSON)
    transition_hint: Mapped[str | None] = mapped_column(String(512))

    opening_templates: Mapped[list | None] = mapped_column(JSON)
    closing_templates: Mapped[list | None] = mapped_column(JSON)

    is_manually_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    plan: Mapped["PitchPlan"] = relationship("PitchPlan", back_populates="pages")

    __table_args__ = (
        Index("idx_plan_page", "plan_id", "page_number"),
    )
