"""add rehearsal.error_msg column for scoring-failure visibility

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-10

Stores the user-facing reason when a rehearsal ends in status=7 (scoring
failed), so the report/history pages can show why instead of a bare failure.
Guarded so it is safe on databases where the column already exists.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("rehearsal")}
    if "error_msg" not in cols:
        op.add_column("rehearsal", sa.Column("error_msg", sa.String(512), nullable=True))


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("rehearsal")}
    if "error_msg" in cols:
        op.drop_column("rehearsal", "error_msg")
