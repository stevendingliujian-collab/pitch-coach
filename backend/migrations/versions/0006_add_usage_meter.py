"""P0 补充: add usage_meter and usage_event tables for free-tier quota tracking

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- usage_meter: monthly running totals per user ---
    op.create_table(
        "usage_meter",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("year_month", sa.String(7), nullable=False),  # "2026-05"
        # Feature counters
        sa.Column("ppt_uploads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rehearsals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("narration_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("knowledge_docs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "year_month", name="uk_user_month"),
    )

    # --- usage_event: append-only audit log ---
    op.create_table(
        "usage_event",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("feature", sa.String(64), nullable=False),   # "ppt_upload", "rehearsal", etc.
        sa.Column("year_month", sa.String(7), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("meta", sa.JSON(), nullable=True),           # extra context (task_id, page_idx)
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_usage_event_user_month", "usage_event", ["user_id", "year_month"])


def downgrade() -> None:
    op.drop_table("usage_event")
    op.drop_table("usage_meter")
