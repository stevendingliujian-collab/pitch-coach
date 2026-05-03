"""add payment table for billing history

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        # 'wechat_pay' | 'alipay' | 'bank_transfer' | 'trial' | 'manual'
        sa.Column("payment_method", sa.String(32), nullable=False, server_default="manual"),
        # 'pending' | 'completed' | 'failed' | 'refunded'
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("plan_type", sa.String(32), nullable=False),
        sa.Column("billing_cycle", sa.String(16), nullable=False, server_default="monthly"),  # monthly | annual
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="CNY"),
        sa.Column("description", sa.String(255), nullable=True),
        # Third-party transaction reference
        sa.Column("transaction_id", sa.String(128), nullable=True),
        sa.Column("invoice_no", sa.String(64), nullable=True, unique=True),
        # Period this payment covers
        sa.Column("period_start", sa.DateTime, nullable=True),
        sa.Column("period_end", sa.DateTime, nullable=True),
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
    op.create_index("idx_payment_tenant", "payment", ["tenant_id"])
    op.create_index("idx_payment_status", "payment", ["status"])


def downgrade() -> None:
    op.drop_table("payment")
