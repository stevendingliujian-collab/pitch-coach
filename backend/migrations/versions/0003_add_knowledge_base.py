"""P1: add knowledge base tables (knowledge_document, knowledge_chunk, golden_script)

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_document",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("doc_type", sa.String(32), nullable=False,
                  comment="bid_doc/lost_bid/whitepaper/case_study/rubric_template/company_profile/competitor_card/glossary"),
        sa.Column("file_name", sa.String(256), nullable=False),
        sa.Column("file_url", sa.String(512), nullable=False),
        sa.Column("file_size", sa.BigInteger),
        sa.Column("chunk_count", sa.Integer, server_default="0"),
        # 0=pending 1=processing 2=done 3=failed
        sa.Column("embedding_status", sa.SmallInteger, server_default="0"),
        sa.Column("industry", sa.String(64)),
        sa.Column("project_type", sa.String(64)),
        sa.Column("tags", sa.JSON),
        sa.Column("description", sa.Text),
        sa.Column("uploaded_by", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_kb_tenant_type", "knowledge_document", ["tenant_id", "doc_type"])
    op.create_index("idx_kb_tenant_industry", "knowledge_document", ["tenant_id", "industry"])

    op.create_table(
        "knowledge_chunk",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("doc_id", sa.BigInteger,
                  sa.ForeignKey("knowledge_document.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_type", sa.String(16), server_default="text",
                  comment="text/table/image_caption"),
        sa.Column("heading", sa.String(256)),
        sa.Column("page_number", sa.Integer),
        # Qdrant point ID (uuid stored as string)
        sa.Column("vector_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_chunk_doc", "knowledge_chunk", ["doc_id"])
    op.create_index("idx_chunk_tenant", "knowledge_chunk", ["tenant_id"])

    op.create_table(
        "golden_script",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger,
                  sa.ForeignKey("rehearsal.id", ondelete="SET NULL"), nullable=True),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("audio_clip_url", sa.String(512)),
        sa.Column("start_sec", sa.Numeric(8, 2)),
        sa.Column("end_sec", sa.Numeric(8, 2)),
        sa.Column("transcript", sa.Text, nullable=False),
        sa.Column("marked_by", sa.BigInteger, nullable=False),
        sa.Column("tags", sa.JSON),
        sa.Column("usage_count", sa.Integer, server_default="0"),
        sa.Column("vector_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_golden_tenant", "golden_script", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("golden_script")
    op.drop_index("idx_chunk_tenant", "knowledge_chunk")
    op.drop_index("idx_chunk_doc", "knowledge_chunk")
    op.drop_table("knowledge_chunk")
    op.drop_index("idx_kb_tenant_industry", "knowledge_document")
    op.drop_index("idx_kb_tenant_type", "knowledge_document")
    op.drop_table("knowledge_document")
