"""P1 F2: add demo_narration table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "demo_narration",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("plan_id", sa.BigInteger,
                  sa.ForeignKey("pitch_plan.id", ondelete="CASCADE"), nullable=False),

        sa.Column("voice_id", sa.String(128), nullable=False),
        sa.Column("voice_name", sa.String(64)),
        sa.Column("speed", sa.Float, nullable=False, server_default="1.0"),

        sa.Column("page_audios", sa.JSON),
        sa.Column("total_audio_url", sa.String(512)),
        sa.Column("total_duration_sec", sa.Integer),

        sa.Column("status", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("error_msg", sa.Text),

        sa.Column("created_by", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_narration_plan", "demo_narration", ["plan_id"])
    op.create_index("idx_narration_tenant", "demo_narration", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("idx_narration_tenant", "demo_narration")
    op.drop_index("idx_narration_plan", "demo_narration")
    op.drop_table("demo_narration")
