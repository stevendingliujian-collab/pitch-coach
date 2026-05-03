"""
Gamification models — achievement definitions, user achievements, stats, leaderboard
"""
from __future__ import annotations
from datetime import datetime
from typing import Any
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, Date, Numeric,
    DateTime, ForeignKey, JSON, UniqueConstraint, func,
)
from app.core.database import Base


class Achievement(Base):
    __tablename__ = "achievement"

    id = Column(Integer, primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    icon_emoji = Column(String(8), default="🏆")
    category = Column(String(32), default="general")
    condition_type = Column(String(64), nullable=False)
    condition_value = Column(Integer, default=1)
    points = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserAchievement(Base):
    __tablename__ = "user_achievement"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("pc_user.id", ondelete="CASCADE"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievement.id", ondelete="CASCADE"), nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    context = Column(JSON, default={})


class UserStats(Base):
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("pc_user.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_rehearsals = Column(Integer, default=0)
    total_practice_sessions = Column(Integer, default=0)
    total_qa_sessions = Column(Integer, default=0)
    best_rehearsal_score = Column(Numeric(5, 2))
    avg_rehearsal_score = Column(Numeric(5, 2))
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    total_achievements = Column(Integer, default=0)
    last_activity_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class LeaderboardSnapshot(Base):
    __tablename__ = "leaderboard_snapshot"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    period_type = Column(String(16), nullable=False)  # week / month / all_time
    period_start = Column(Date, nullable=False)
    user_id = Column(Integer, ForeignKey("pc_user.id", ondelete="CASCADE"), nullable=False)
    rank = Column(Integer, nullable=False)
    score = Column(Numeric(8, 2), default=0)
    rehearsal_count = Column(Integer, default=0)
    avg_score = Column(Numeric(5, 2))
    points_earned = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
