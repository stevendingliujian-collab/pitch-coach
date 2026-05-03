"""add review_comment and certification tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── review_comment ────────────────────────────────────────────────────
    op.create_table(
        "review_comment",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("rehearsal_id", sa.BigInteger(),
                  sa.ForeignKey("rehearsal.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.BigInteger(), nullable=False),
        sa.Column("timestamp_sec", sa.Numeric(8, 2), nullable=False),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("is_highlight", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mentioned_users", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_rehearsal_comment", "review_comment", ["rehearsal_id"])

    # ── certification ─────────────────────────────────────────────────────
    op.create_table(
        "certification",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("pitch_task_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("reviewer_id", sa.BigInteger(), nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger(),
                  sa.ForeignKey("rehearsal.id"), nullable=False),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("certified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "pitch_task_id", "user_id",
                            name="uk_task_user_cert"),
    )

    # ── rehearsal: submitted_at column ────────────────────────────────────
    # Add submitted_at if not already present (safe to call multiple times via
    # the nullable=True server_default=None path — will no-op if column exists)
    try:
        op.add_column("rehearsal",
                      sa.Column("submitted_at", sa.DateTime(), nullable=True))
    except Exception:
        pass  # Column already exists from a previous partial migration


def downgrade() -> None:
    op.drop_table("certification")
    op.drop_index("idx_rehearsal_comment", "review_comment")
    op.drop_table("review_comment")
    try:
        op.drop_column("rehearsal", "submitted_at")
    except Exception:
        pass
