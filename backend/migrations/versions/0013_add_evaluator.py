"""add evaluator_persona and qa_session tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── evaluator_persona ─────────────────────────────────────────────────────
    op.create_table(
        "evaluator_persona",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        # 'system' personas are global presets; 'custom' belong to a tenant
        sa.Column("persona_type", sa.String(32), nullable=False, server_default="custom"),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("role", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("avatar_emoji", sa.String(8), nullable=True, server_default="🧑‍⚖️"),
        # Difficulty 1-5
        sa.Column("difficulty", sa.SmallInteger, nullable=False, server_default="3"),
        # Focus areas for generating questions
        sa.Column("focus_areas", sa.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.BigInteger, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_evaluator_tenant", "evaluator_persona", ["tenant_id"])
    op.create_index("idx_evaluator_type", "evaluator_persona", ["persona_type"])

    # ── qa_session ────────────────────────────────────────────────────────────
    op.create_table(
        "qa_session",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("pitch_task_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column(
            "evaluator_id",
            sa.BigInteger,
            sa.ForeignKey("evaluator_persona.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # 'single' | 'panel' (multi-evaluator)
        sa.Column("session_type", sa.String(16), nullable=False, server_default="single"),
        # JSON array: [{role, content, audio_url?, score?}]
        sa.Column("messages", sa.JSON, nullable=False, server_default="[]"),
        # 0=init 1=in_progress 2=completed
        sa.Column("status", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_qa_tenant_task", "qa_session", ["tenant_id", "pitch_task_id"])
    op.create_index("idx_qa_user", "qa_session", ["user_id"])


def downgrade() -> None:
    op.drop_table("qa_session")
    op.drop_table("evaluator_persona")
