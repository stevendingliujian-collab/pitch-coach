"""P1: add conversion triggers, trigger events, and analytics events

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # upgrade_trigger: tracks which trigger points have been shown to which users
    op.create_table(
        "upgrade_trigger",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        # T1-T9 trigger IDs from the plan
        sa.Column("trigger_id", sa.String(16), nullable=False),
        sa.Column("show_count", sa.Integer, server_default="0"),
        sa.Column("max_shows", sa.Integer, server_default="1"),
        sa.Column("converted", sa.Boolean, server_default="false"),
        sa.Column("last_shown_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_upgrade_trigger_user", "upgrade_trigger", ["user_id", "trigger_id"], unique=True)
    op.create_index("idx_upgrade_trigger_tenant", "upgrade_trigger", ["tenant_id"])

    # trigger_event: immutable log of when triggers were shown/dismissed/converted
    op.create_table(
        "trigger_event",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("trigger_id", sa.String(16), nullable=False),
        # shown / dismissed / converted
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("meta", sa.JSON),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_trigger_event_user", "trigger_event", ["user_id", "trigger_id"])

    # analytics_event: lightweight funnel tracking
    op.create_table(
        "analytics_event",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        # e.g. "user_registered", "ppt_uploaded", "plan_generated",
        #      "rehearsal_completed", "daily_practice_done", "upgrade_clicked"
        sa.Column("event_name", sa.String(64), nullable=False),
        sa.Column("properties", sa.JSON),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_analytics_event_user", "analytics_event", ["user_id", "event_name"])
    op.create_index("idx_analytics_event_tenant_time", "analytics_event", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_analytics_event_tenant_time", "analytics_event")
    op.drop_index("idx_analytics_event_user", "analytics_event")
    op.drop_table("analytics_event")

    op.drop_index("idx_trigger_event_user", "trigger_event")
    op.drop_table("trigger_event")

    op.drop_index("idx_upgrade_trigger_tenant", "upgrade_trigger")
    op.drop_index("idx_upgrade_trigger_user", "upgrade_trigger")
    op.drop_table("upgrade_trigger")
