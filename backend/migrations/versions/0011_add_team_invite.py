"""add team_invite table for invite-link join flow

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_invite",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),   # user_id
        # invite_code is a short alphanumeric slug (12 chars)
        sa.Column("invite_code", sa.String(32), nullable=False, unique=True),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        # role granted to new members who join via this invite
        sa.Column("grant_role", sa.String(32), nullable=False, server_default="presenter"),
        sa.Column("note", sa.String(256), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_invite_tenant", "team_invite", ["tenant_id"])
    op.create_index("uk_invite_code", "team_invite", ["invite_code"], unique=True)


def downgrade() -> None:
    op.drop_index("uk_invite_code", "team_invite")
    op.drop_index("idx_invite_tenant", "team_invite")
    op.drop_table("team_invite")
