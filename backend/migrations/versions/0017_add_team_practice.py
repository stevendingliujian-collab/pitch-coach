"""add team practice tables

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # team_practice_session
    op.create_table(
        "team_practice_session",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("pitch_task_id", sa.BigInteger, nullable=False),
        sa.Column("created_by", sa.BigInteger, nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("roles", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("status", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("avg_score", sa.Float, nullable=True),
        sa.Column("total_score", sa.Float, nullable=True),
        sa.Column("feedback", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_tps_tenant", "team_practice_session", ["tenant_id"])
    op.create_index("ix_tps_task", "team_practice_session", ["pitch_task_id"])

    # team_practice_participant
    op.create_table(
        "team_practice_participant",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.BigInteger, nullable=False),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("role_index", sa.Integer, nullable=False),
        sa.Column("role_name", sa.String(128), nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger, nullable=True),
        sa.Column("status", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("joined_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("submitted_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_tpp_session", "team_practice_participant", ["session_id"])
    op.create_index("ix_tpp_user", "team_practice_participant", ["user_id"])


def downgrade() -> None:
    op.drop_table("team_practice_participant")
    op.drop_table("team_practice_session")
