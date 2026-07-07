"""add review_comment and certification tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-03

Note: review_comment / certification (and rehearsal.submitted_at) are already
created by 0001 in current deployments. This revision originally duplicated
those CREATE TABLE statements, which broke fresh installs (table already
exists). It is now guarded: each object is only created if missing, so the
migration works both on fresh databases (no-op) and on legacy databases that
predate these tables.
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    inspector = _inspector()
    tables = inspector.get_table_names()

    if "review_comment" not in tables:
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

    if "certification" not in tables:
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

    rehearsal_columns = {c["name"] for c in inspector.get_columns("rehearsal")}
    if "submitted_at" not in rehearsal_columns:
        op.add_column("rehearsal",
                      sa.Column("submitted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    # These objects are owned by 0001 in current deployments; dropping them
    # here would destroy data created before this revision. No-op.
    pass
