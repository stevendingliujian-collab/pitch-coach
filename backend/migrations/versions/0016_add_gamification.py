"""Add gamification tables: achievement, user_achievement, leaderboard_snapshot, user_stats

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    # ─── achievement (badge definitions) ─────────────────────────────────────
    op.create_table(
        "achievement",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("icon_emoji", sa.String(8), default="🏆"),
        sa.Column("category", sa.String(32), default="general"),
        sa.Column("condition_type", sa.String(64), nullable=False),
        sa.Column("condition_value", sa.Integer, default=1),
        sa.Column("points", sa.Integer, default=10),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    # ─── user_achievement (earned by users) ───────────────────────────────────
    op.create_table(
        "user_achievement",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer,
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer,
                  sa.ForeignKey("pc_user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("achievement_id", sa.Integer,
                  sa.ForeignKey("achievement.id", ondelete="CASCADE"), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("context", sa.JSON, default={}),
        sa.UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )
    op.create_index("ix_user_achievement_tenant", "user_achievement", ["tenant_id"])
    op.create_index("ix_user_achievement_user", "user_achievement", ["user_id"])

    # ─── user_stats (aggregate per-user stats for leaderboard) ───────────────
    op.create_table(
        "user_stats",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer,
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer,
                  sa.ForeignKey("pc_user.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("total_rehearsals", sa.Integer, default=0),
        sa.Column("total_practice_sessions", sa.Integer, default=0),
        sa.Column("total_qa_sessions", sa.Integer, default=0),
        sa.Column("best_rehearsal_score", sa.Numeric(5, 2)),
        sa.Column("avg_rehearsal_score", sa.Numeric(5, 2)),
        sa.Column("current_streak", sa.Integer, default=0),
        sa.Column("longest_streak", sa.Integer, default=0),
        sa.Column("total_points", sa.Integer, default=0),
        sa.Column("total_achievements", sa.Integer, default=0),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_user_stats_tenant", "user_stats", ["tenant_id"])

    # ─── leaderboard_snapshot (weekly / monthly aggregates) ──────────────────
    op.create_table(
        "leaderboard_snapshot",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer,
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_type", sa.String(16), nullable=False),  # week / month / all_time
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("user_id", sa.Integer,
                  sa.ForeignKey("pc_user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("score", sa.Numeric(8, 2), default=0),
        sa.Column("rehearsal_count", sa.Integer, default=0),
        sa.Column("avg_score", sa.Numeric(5, 2)),
        sa.Column("points_earned", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_index("ix_leaderboard_tenant_period",
                    "leaderboard_snapshot", ["tenant_id", "period_type", "period_start"])

    # ─── Seed achievement definitions ────────────────────────────────────────
    op.execute("""
        INSERT INTO achievement (code, name, description, icon_emoji, category, condition_type, condition_value, points) VALUES
        ('first_win',       '首胜',       '第一次排练得分≥80', '🏆', 'rehearsal', 'rehearsal_score_gte', 80, 20),
        ('five_streak',     '五连胜',     '连续5次排练得分≥75', '🔥', 'streak',   'rehearsal_streak_gte', 5, 50),
        ('no_filler',       '无废话',     '一次排练填充词≤2个', '🎯', 'quality',  'filler_words_lte', 2, 30),
        ('golden_teacher',  '金牌讲师',   '有10条话术被经理标记为精彩', '🌟', 'knowledge', 'golden_scripts_gte', 10, 100),
        ('speed_presenter', '闪电述标',   '限时模式排练得分≥85', '⚡', 'rehearsal', 'timed_score_gte', 85, 40),
        ('rubric_master',   '评分表大师', '一次排练评分表覆盖率100%', '📋', 'quality',  'rubric_coverage_eq', 100, 60),
        ('qa_warrior',      '答疑战士',   '连续5次评委问答总分≥85', '🛡️', 'evaluator', 'qa_streak_gte', 5, 50),
        ('early_bird',      '早鸟练习者', '连续7天完成每日微练习', '🌅', 'practice', 'daily_streak_gte', 7, 40),
        ('centurion',       '百次排练',   '累计完成100次排练', '💯', 'milestone', 'total_rehearsals_gte', 100, 200)
    """)


def downgrade():
    op.drop_table("leaderboard_snapshot")
    op.drop_table("user_stats")
    op.drop_index("ix_user_achievement_user", "user_achievement")
    op.drop_index("ix_user_achievement_tenant", "user_achievement")
    op.drop_table("user_achievement")
    op.drop_table("achievement")
