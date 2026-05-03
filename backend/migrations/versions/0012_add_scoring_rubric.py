"""add scoring_rubric and rubric_score tables

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scoring_rubric",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        # 'manual' | 'pdf_parsed' | 'template'
        sa.Column("source_type", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("source_file_url", sa.String(512), nullable=True),
        # JSON array of rubric items: [{id, category, item, max_score, weight, description}]
        sa.Column("items", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("total_max_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("industry", sa.String(64), nullable=True),
        # preset templates: 'system_integration' | 'software_dev' | 'automation' | 'custom'
        sa.Column("template_type", sa.String(64), nullable=True),
        sa.Column("is_template", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_by", sa.BigInteger, nullable=True),
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
    op.create_index("idx_rubric_tenant", "scoring_rubric", ["tenant_id"])
    op.create_index("idx_rubric_template", "scoring_rubric", ["is_template"])

    op.create_table(
        "rubric_score",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column(
            "rubric_id",
            sa.BigInteger,
            sa.ForeignKey("scoring_rubric.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rehearsal_id",
            sa.BigInteger,
            sa.ForeignKey("rehearsal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # [{item_id, score, coverage, note, suggest_page}]
        sa.Column("scores", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=True),
        # 0.0 – 1.0
        sa.Column("coverage_percent", sa.Numeric(4, 3), nullable=True),
        # [{item_id, covered, evidence}]
        sa.Column("coverage_detail", sa.JSON, nullable=True),
        # [{item_id, suggestion}]
        sa.Column("improvement_suggestions", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_rubric_score_rehearsal", "rubric_score", ["rehearsal_id"])
    op.create_index("idx_rubric_score_rubric", "rubric_score", ["rubric_id"])
    op.create_index(
        "uk_rubric_score_rubric_rehearsal",
        "rubric_score",
        ["rubric_id", "rehearsal_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("rubric_score")
    op.drop_table("scoring_rubric")
