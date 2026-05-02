"""initial schema: P0 core tables

Revision ID: 0001
Revises:
Create Date: 2026-05-02
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("industry", sa.String(64)),
        sa.Column("plan_type", sa.String(32), nullable=False, server_default="free"),
        sa.Column("max_users", sa.Integer, nullable=False, server_default="3"),
        sa.Column("max_rehearsals_month", sa.Integer, nullable=False, server_default="10"),
        sa.Column("integration_type", sa.String(32)),
        sa.Column("integration_config", sa.JSON),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime),
    )

    op.create_table(
        "pc_user",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False, index=True),
        sa.Column("email", sa.String(128)),
        sa.Column("phone", sa.String(20)),
        sa.Column("password_hash", sa.String(256)),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="member"),
        sa.Column("avatar_url", sa.String(512)),
        sa.Column("external_user_id", sa.String(128)),
        sa.Column("sso_provider", sa.String(32)),
        sa.Column("status", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("last_login_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uk_tenant_email", "pc_user", ["tenant_id", "email"])
    op.create_unique_constraint("uk_tenant_phone", "pc_user", ["tenant_id", "phone"])
    op.create_unique_constraint("uk_external", "pc_user", ["tenant_id", "sso_provider", "external_user_id"])

    op.create_table(
        "pitch_task",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("customer_name", sa.String(128)),
        sa.Column("customer_industry", sa.String(64)),
        sa.Column("budget", sa.Numeric(14, 2)),
        sa.Column("bid_date", sa.Date),
        sa.Column("bid_time_limit", sa.SmallInteger),
        sa.Column("bid_requirements", sa.Text),
        sa.Column("competitor_info", sa.JSON),
        sa.Column("result", sa.SmallInteger),
        sa.Column("external_id", sa.String(128)),
        sa.Column("external_type", sa.String(32)),
        sa.Column("owner_id", sa.BigInteger, nullable=False),
        sa.Column("member_ids", sa.JSON),
        sa.Column("status", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_tenant_status_task", "pitch_task", ["tenant_id", "status"])
    op.create_index("idx_bid_date", "pitch_task", ["tenant_id", "bid_date"])
    op.create_unique_constraint("uk_external_task", "pitch_task", ["tenant_id", "external_type", "external_id"])

    op.create_table(
        "pitch_plan",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("pitch_task_id", sa.BigInteger, nullable=False),
        sa.Column("ppt_file_id", sa.String(128), nullable=False),
        sa.Column("ppt_file_name", sa.String(256), nullable=False),
        sa.Column("ppt_page_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("customer_name", sa.String(128)),
        sa.Column("customer_industry", sa.String(64)),
        sa.Column("project_budget", sa.Numeric(14, 2)),
        sa.Column("bid_requirements", sa.Text),
        sa.Column("bid_time_limit", sa.Integer),
        sa.Column("competitor_info", sa.JSON),
        sa.Column("global_strategy", sa.Text),
        sa.Column("total_duration_sec", sa.Integer),
        sa.Column("predicted_questions", sa.JSON),
        sa.Column("competitive_differentiation", sa.JSON),
        sa.Column("opening_templates", sa.JSON),
        sa.Column("closing_templates", sa.JSON),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("created_by", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_tenant_task_plan", "pitch_plan", ["tenant_id", "pitch_task_id"])

    op.create_table(
        "plan_page",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("plan_id", sa.BigInteger, sa.ForeignKey("pitch_plan.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("page_title", sa.String(256)),
        sa.Column("page_content_summary", sa.Text),
        sa.Column("page_thumbnail_url", sa.String(512)),
        sa.Column("importance_level", sa.SmallInteger, nullable=False, server_default="2"),
        sa.Column("talking_points", sa.JSON, nullable=False),
        sa.Column("suggested_duration", sa.Integer, nullable=False, server_default="60"),
        sa.Column("emphasis_marks", sa.JSON),
        sa.Column("bid_req_mapping", sa.JSON),
        sa.Column("transition_hint", sa.String(512)),
        sa.Column("opening_templates", sa.JSON),
        sa.Column("closing_templates", sa.JSON),
        sa.Column("is_manually_edited", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_plan_page", "plan_page", ["plan_id", "page_number"])

    op.create_table(
        "rehearsal",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("pitch_task_id", sa.BigInteger, nullable=False),
        sa.Column("plan_id", sa.BigInteger),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("audio_url", sa.String(512), nullable=False),
        sa.Column("audio_duration", sa.Integer, nullable=False),
        sa.Column("video_url", sa.String(512)),
        sa.Column("page_timings", sa.JSON, nullable=False),
        sa.Column("transcript_json", sa.JSON),
        sa.Column("total_score", sa.Numeric(5, 2)),
        sa.Column("dimension_scores", sa.JSON),
        sa.Column("page_scores", sa.JSON),
        sa.Column("improvement_tips", sa.JSON),
        sa.Column("filler_word_count", sa.Integer),
        sa.Column("filler_word_detail", sa.JSON),
        sa.Column("status", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("submitted_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_tenant_task_rehearsal", "rehearsal", ["tenant_id", "pitch_task_id"])
    op.create_index("idx_user_rehearsal", "rehearsal", ["tenant_id", "user_id"])

    op.create_table(
        "review_comment",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("rehearsal_id", sa.BigInteger, sa.ForeignKey("rehearsal.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.BigInteger, nullable=False),
        sa.Column("timestamp_sec", sa.Numeric(8, 2), nullable=False),
        sa.Column("comment_text", sa.Text, nullable=False),
        sa.Column("is_highlight", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("mentioned_users", sa.JSON),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_rehearsal_comment", "review_comment", ["rehearsal_id"])

    op.create_table(
        "certification",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("pitch_task_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("reviewer_id", sa.BigInteger, nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger, sa.ForeignKey("rehearsal.id"), nullable=False),
        sa.Column("status", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("review_comment", sa.Text),
        sa.Column("certified_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uk_task_user_cert", "certification", ["tenant_id", "pitch_task_id", "user_id"])

    op.create_table(
        "win_loss_record",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("pitch_task_id", sa.BigInteger, nullable=False),
        sa.Column("result", sa.SmallInteger, nullable=False),
        sa.Column("bid_score_total", sa.Numeric(5, 2)),
        sa.Column("bid_score_business", sa.Numeric(5, 2)),
        sa.Column("bid_score_technical", sa.Numeric(5, 2)),
        sa.Column("bid_score_pitch", sa.Numeric(5, 2)),
        sa.Column("loss_reason_code", sa.String(32)),
        sa.Column("loss_reason_detail", sa.Text),
        sa.Column("best_rehearsal_id", sa.BigInteger),
        sa.Column("best_rehearsal_score", sa.Numeric(5, 2)),
        sa.Column("rehearsal_count", sa.Integer),
        sa.Column("competitor_names", sa.JSON),
        sa.Column("winning_competitor", sa.String(128)),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uk_task_win_loss", "win_loss_record", ["tenant_id", "pitch_task_id"])
    op.create_index("idx_result", "win_loss_record", ["tenant_id", "result"])


def downgrade() -> None:
    for table in ["win_loss_record", "certification", "review_comment",
                  "rehearsal", "plan_page", "pitch_plan", "pitch_task", "pc_user", "tenant"]:
        op.drop_table(table)
