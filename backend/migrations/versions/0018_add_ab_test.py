"""add ab_test and ab_test_assignment tables

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A/B test definitions
    op.create_table(
        "ab_test",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("variants", sa.JSON, nullable=False, server_default='[]'),
        sa.Column("weights", sa.JSON, nullable=True),          # e.g. [50, 50] or [33, 33, 34]
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("start_date", sa.DateTime, nullable=True),
        sa.Column("end_date", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # User → variant assignments (one row per user per test)
    op.create_table(
        "ab_test_assignment",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("test_name", sa.String(128), nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("variant", sa.String(64), nullable=False),
        sa.Column("assigned_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ab_assign_user_test", "ab_test_assignment",
                    ["user_id", "test_name"], unique=True)
    op.create_index("ix_ab_assign_tenant_test", "ab_test_assignment",
                    ["tenant_id", "test_name"])

    # Conversion events for tracking which variant converts better
    op.create_table(
        "ab_test_event",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("test_name", sa.String(128), nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("variant", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),  # e.g. "conversion", "click"
        sa.Column("meta", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ab_event_test_variant", "ab_test_event",
                    ["test_name", "variant"])

    # Seed two default tests used by the product
    op.execute("""
        INSERT INTO ab_test (name, description, variants, weights, is_active)
        VALUES
          ('pricing_layout', '定价页布局测试：A=ROI对比在上 B=套餐卡片在上',
           '["control","variant_b"]', '[50,50]', true),
          ('onboarding_steps', '引导步骤测试：A=3步引导 B=1步快速引导',
           '["control","variant_b"]', '[50,50]', true),
          ('upgrade_cta_copy', '升级按钮文案测试：A=立即升级 B=7天免费试用',
           '["control","variant_b"]', '[50,50]', true)
    """)


def downgrade() -> None:
    op.drop_table("ab_test_event")
    op.drop_index("ix_ab_assign_tenant_test", table_name="ab_test_assignment")
    op.drop_index("ix_ab_assign_user_test", table_name="ab_test_assignment")
    op.drop_table("ab_test_assignment")
    op.drop_table("ab_test")
