"""add subscription table for trial/paid plans

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        # status: free | trial | active | cancelled | expired
        sa.Column("status", sa.String(32), nullable=False, server_default="free"),
        sa.Column("plan_type", sa.String(32), nullable=False, server_default="free"),
        sa.Column("trial_starts_at", sa.DateTime(), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("now()"), onupdate=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", name="uk_subscription_tenant"),
    )
    op.create_index("idx_subscription_tenant", "subscription", ["tenant_id"])
    op.create_index("idx_subscription_status", "subscription", ["status"])


def downgrade() -> None:
    op.drop_index("idx_subscription_status", "subscription")
    op.drop_index("idx_subscription_tenant", "subscription")
    op.drop_table("subscription")
