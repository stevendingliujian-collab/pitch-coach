"""P1 F3: add training_plan and training_session tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_plan",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("pitch_task_id", sa.BigInteger,
                  sa.ForeignKey("pitch_task.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.BigInteger,
                  sa.ForeignKey("pitch_plan.id", ondelete="SET NULL"), nullable=True),
        sa.Column("first_practice_date", sa.Date),
        sa.Column("bid_date", sa.Date),
        sa.Column("schedule_dates", sa.JSON),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_training_plan_user_task", "training_plan", ["user_id", "pitch_task_id"])
    op.create_index("idx_training_plan_tenant", "training_plan", ["tenant_id"])

    op.create_table(
        "training_session",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("plan_id", sa.BigInteger,
                  sa.ForeignKey("training_plan.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("pitch_task_id", sa.BigInteger, nullable=False),
        sa.Column("mode", sa.String(16), nullable=False,
                  comment="follow=跟读 recite=背诵"),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("audio_url", sa.String(512)),
        sa.Column("transcript", sa.Text),
        sa.Column("total_score", sa.Numeric(5, 2)),
        sa.Column("dimension_scores", sa.JSON),
        sa.Column("feedback", sa.JSON),
        sa.Column("practice_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_ts_plan", "training_session", ["plan_id"])
    op.create_index("idx_ts_user_date", "training_session", ["user_id", "practice_date"])


def downgrade() -> None:
    op.drop_index("idx_ts_user_date", "training_session")
    op.drop_index("idx_ts_plan", "training_session")
    op.drop_table("training_session")
    op.drop_index("idx_training_plan_tenant", "training_plan")
    op.drop_index("idx_training_plan_user_task", "training_plan")
    op.drop_table("training_plan")
