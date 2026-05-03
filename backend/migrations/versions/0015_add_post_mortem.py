"""add post_mortem and api_key tables for P3

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── post_mortem: 述标复盘报告 ──────────────────────────────────────────
    op.create_table(
        "post_mortem",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("pitch_task_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        # Audio upload of the actual pitch meeting recording
        sa.Column("recording_url", sa.String(512), nullable=True),
        sa.Column("recording_duration", sa.Integer, nullable=True),  # seconds
        # Processing status: pending | processing | completed | failed
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        # Speaker diarization result: [{speaker, start, end, text}]
        sa.Column("diarization", sa.JSON, nullable=True),
        # Extracted evaluator questions: [{category, question, start_time, answer_quality, notes}]
        sa.Column("evaluator_questions", sa.JSON, nullable=True),
        # Summary stats
        sa.Column("our_talk_ratio", sa.Numeric(5, 2), nullable=True),   # % of time we talked
        sa.Column("evaluator_count", sa.Integer, nullable=True),         # distinct evaluator speakers
        sa.Column("question_count", sa.Integer, nullable=True),
        # Question category breakdown: {tech, business, user, compliance, other}
        sa.Column("question_categories", sa.JSON, nullable=True),
        # Predicted vs actual: which rehearsal Q&A predictions were correct
        sa.Column("prediction_hit_rate", sa.Numeric(5, 2), nullable=True),
        # Answer quality assessment: [{question_id, score, feedback, reference_from_kb}]
        sa.Column("answer_assessments", sa.JSON, nullable=True),
        # Draft follow-up letter
        sa.Column("followup_draft", sa.Text, nullable=True),
        # Key moments and highlights
        sa.Column("key_moments", sa.JSON, nullable=True),
        # Overall insights
        sa.Column("insights", sa.JSON, nullable=True),
        # Celery task id for async processing
        sa.Column("task_id", sa.String(64), nullable=True),
        sa.Column("error_msg", sa.String(512), nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_index("idx_pm_tenant", "post_mortem", ["tenant_id"])
    op.create_index("idx_pm_task", "post_mortem", ["pitch_task_id"])
    op.create_index("idx_pm_status", "post_mortem", ["status"])

    # ── api_key: Open API 密钥 ────────────────────────────────────────────
    op.create_table(
        "api_key",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),  # SHA-256 of full key
        sa.Column("key_prefix", sa.String(12), nullable=False),             # First 12 chars for display
        sa.Column("scopes", sa.JSON, nullable=False, server_default="[]"),  # ['read', 'write', 'webhook']
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_index("idx_apikey_tenant", "api_key", ["tenant_id"])

    # ── api_usage: Open API 用量计量 ──────────────────────────────────────
    op.create_table(
        "api_usage",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("api_key_id", sa.BigInteger, nullable=False),
        sa.Column("endpoint", sa.String(128), nullable=False),
        sa.Column("method", sa.String(8), nullable=False),
        sa.Column("status_code", sa.SmallInteger, nullable=False),
        sa.Column("response_ms", sa.Integer, nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_index("idx_apiusage_tenant", "api_usage", ["tenant_id"])
    op.create_index("idx_apiusage_key", "api_usage", ["api_key_id"])


def downgrade() -> None:
    op.drop_table("api_usage")
    op.drop_table("api_key")
    op.drop_table("post_mortem")
