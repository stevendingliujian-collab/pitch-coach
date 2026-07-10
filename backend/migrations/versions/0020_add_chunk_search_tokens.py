"""add knowledge_chunk.search_tokens for Chinese full-text search

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-10

Stores space-joined jieba tokens of each chunk so PostgreSQL's `simple` FTS
config can match Chinese queries without a DB-side segmenter extension. Nullable
so existing rows keep working (keyword search falls back to `content`);
re-ingest old documents to populate tokens for them.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("knowledge_chunk")}
    if "search_tokens" not in cols:
        op.add_column("knowledge_chunk", sa.Column("search_tokens", sa.Text(), nullable=True))


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("knowledge_chunk")}
    if "search_tokens" in cols:
        op.drop_column("knowledge_chunk", "search_tokens")
