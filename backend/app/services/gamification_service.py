"""
Gamification Service — badge rules engine + leaderboard + streak fire

徽章规则引擎：
- 首胜 (first_win): 排练得分≥80
- 五连胜 (five_streak): 连续5次排练得分≥75
- 无废话 (no_filler): 一次排练填充词≤2
- 金牌讲师 (golden_teacher): 10条话术被标记精彩
- 闪电述标 (speed_presenter): 限时模式得分≥85
- 评分表大师 (rubric_master): 单次评分表覆盖率100%
- 答疑战士 (qa_warrior): 连续5次QA总分≥85
- 早鸟练习者 (early_bird): 连续7天完成每日微练习
- 百次排练 (centurion): 累计100次排练
"""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import Achievement, UserAchievement, UserStats, LeaderboardSnapshot
from app.models.post_mortem import ApiKey  # just to verify imports work

logger = logging.getLogger(__name__)


# ─── Achievement check helpers ────────────────────────────────────────────────

async def _already_earned(db: AsyncSession, user_id: int, achievement_id: int) -> bool:
    result = await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def _award(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    achievement: Achievement,
    context: dict | None = None,
) -> UserAchievement | None:
    """Award an achievement if not already earned. Returns the record or None."""
    if await _already_earned(db, user_id, achievement.id):
        return None

    ua = UserAchievement(
        tenant_id=tenant_id,
        user_id=user_id,
        achievement_id=achievement.id,
        context=context or {},
    )
    db.add(ua)

    # Update user_stats points + count
    stats = await _get_or_create_stats(db, tenant_id, user_id)
    stats.total_points = (stats.total_points or 0) + achievement.points
    stats.total_achievements = (stats.total_achievements or 0) + 1

    await db.flush()
    logger.info("Achievement awarded: user=%s badge=%s", user_id, achievement.code)
    return ua


async def _get_achievement(db: AsyncSession, code: str) -> Achievement | None:
    result = await db.execute(
        select(Achievement).where(Achievement.code == code, Achievement.is_active == True)
    )
    return result.scalar_one_or_none()


# ─── Stats helpers ────────────────────────────────────────────────────────────

async def _get_or_create_stats(db: AsyncSession, tenant_id: int, user_id: int) -> UserStats:
    result = await db.execute(
        select(UserStats).where(UserStats.user_id == user_id)
    )
    stats = result.scalar_one_or_none()
    if not stats:
        stats = UserStats(tenant_id=tenant_id, user_id=user_id)
        db.add(stats)
        await db.flush()
    return stats


# ─── Rule checks ─────────────────────────────────────────────────────────────

async def check_rehearsal_achievements(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    score: float,
    filler_word_count: int = 0,
    is_timed: bool = False,
    rubric_coverage: float | None = None,
) -> list[dict]:
    """
    Call after a rehearsal is scored. Returns list of newly earned badge dicts.
    """
    new_badges: list[dict] = []

    # Update stats
    stats = await _get_or_create_stats(db, tenant_id, user_id)
    stats.total_rehearsals = (stats.total_rehearsals or 0) + 1
    stats.last_activity_at = datetime.utcnow()

    # best score
    cur_best = float(stats.best_rehearsal_score or 0)
    if score > cur_best:
        stats.best_rehearsal_score = score

    # avg score (rolling avg)
    n = stats.total_rehearsals
    cur_avg = float(stats.avg_rehearsal_score or 0)
    stats.avg_rehearsal_score = round((cur_avg * (n - 1) + score) / n, 2)

    await db.flush()

    # first_win
    ach = await _get_achievement(db, "first_win")
    if ach and score >= 80:
        ua = await _award(db, tenant_id, user_id, ach, {"score": score})
        if ua:
            new_badges.append(_badge_dict(ach))

    # no_filler
    ach = await _get_achievement(db, "no_filler")
    if ach and filler_word_count <= 2:
        ua = await _award(db, tenant_id, user_id, ach, {"filler_count": filler_word_count})
        if ua:
            new_badges.append(_badge_dict(ach))

    # speed_presenter (timed mode)
    if is_timed and score >= 85:
        ach = await _get_achievement(db, "speed_presenter")
        if ach:
            ua = await _award(db, tenant_id, user_id, ach, {"score": score})
            if ua:
                new_badges.append(_badge_dict(ach))

    # rubric_master
    if rubric_coverage is not None and rubric_coverage >= 100:
        ach = await _get_achievement(db, "rubric_master")
        if ach:
            ua = await _award(db, tenant_id, user_id, ach, {"coverage": rubric_coverage})
            if ua:
                new_badges.append(_badge_dict(ach))

    # centurion
    if stats.total_rehearsals >= 100:
        ach = await _get_achievement(db, "centurion")
        if ach:
            ua = await _award(db, tenant_id, user_id, ach, {"count": stats.total_rehearsals})
            if ua:
                new_badges.append(_badge_dict(ach))

    # streak-based: fetch last N rehearsal scores
    await check_streak_achievements(db, tenant_id, user_id, score, new_badges)

    await db.commit()
    return new_badges


async def check_streak_achievements(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    latest_score: float,
    new_badges: list[dict],
) -> None:
    """Check five_streak by looking at recent rehearsal scores from DB."""
    from app.models.rehearsal import Rehearsal  # local import to avoid circular

    result = await db.execute(
        select(Rehearsal)
        .where(
            Rehearsal.tenant_id == tenant_id,
            Rehearsal.user_id == user_id,
            Rehearsal.status == "scored",
            Rehearsal.total_score.is_not(None),
        )
        .order_by(Rehearsal.id.desc())
        .limit(5)
    )
    recent = result.scalars().all()
    recent_scores = [float(r.total_score) for r in recent if r.total_score is not None]

    # Update current_streak in stats
    stats = await _get_or_create_stats(db, tenant_id, user_id)
    if latest_score >= 75:
        stats.current_streak = (stats.current_streak or 0) + 1
        if stats.current_streak > (stats.longest_streak or 0):
            stats.longest_streak = stats.current_streak
    else:
        stats.current_streak = 0
    await db.flush()

    # five_streak: last 5 all ≥75
    if len(recent_scores) >= 5 and all(s >= 75 for s in recent_scores[:5]):
        ach = await _get_achievement(db, "five_streak")
        if ach:
            ua = await _award(db, tenant_id, user_id, ach, {"scores": recent_scores[:5]})
            if ua:
                new_badges.append(_badge_dict(ach))


async def check_qa_achievements(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    qa_score: float,
) -> list[dict]:
    """Call after a QA session is scored."""
    new_badges: list[dict] = []

    stats = await _get_or_create_stats(db, tenant_id, user_id)
    stats.total_qa_sessions = (stats.total_qa_sessions or 0) + 1
    stats.last_activity_at = datetime.utcnow()
    await db.flush()

    # qa_warrior: fetch last 5 QA session scores
    from app.models.evaluator import QaSession

    result = await db.execute(
        select(QaSession)
        .where(
            QaSession.tenant_id == tenant_id,
            QaSession.user_id == user_id,
            QaSession.status == "completed",
            QaSession.total_score.is_not(None),
        )
        .order_by(QaSession.id.desc())
        .limit(5)
    )
    recent = result.scalars().all()
    recent_scores = [float(s.total_score) for s in recent if s.total_score is not None]

    if len(recent_scores) >= 5 and all(s >= 85 for s in recent_scores[:5]):
        ach = await _get_achievement(db, "qa_warrior")
        if ach:
            ua = await _award(db, tenant_id, user_id, ach, {"scores": recent_scores[:5]})
            if ua:
                new_badges.append(_badge_dict(ach))

    await db.commit()
    return new_badges


async def check_daily_practice_achievements(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    current_streak: int,
) -> list[dict]:
    """Call after a daily practice session is completed."""
    new_badges: list[dict] = []

    stats = await _get_or_create_stats(db, tenant_id, user_id)
    stats.total_practice_sessions = (stats.total_practice_sessions or 0) + 1
    stats.last_activity_at = datetime.utcnow()
    await db.flush()

    if current_streak >= 7:
        ach = await _get_achievement(db, "early_bird")
        if ach:
            ua = await _award(db, tenant_id, user_id, ach, {"streak": current_streak})
            if ua:
                new_badges.append(_badge_dict(ach))

    await db.commit()
    return new_badges


async def check_golden_script_achievements(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    golden_script_count: int,
) -> list[dict]:
    """Call when a golden script is added."""
    new_badges: list[dict] = []

    if golden_script_count >= 10:
        ach = await _get_achievement(db, "golden_teacher")
        if ach:
            ua = await _award(db, tenant_id, user_id, ach, {"count": golden_script_count})
            if ua:
                new_badges.append(_badge_dict(ach))

    await db.commit()
    return new_badges


# ─── Leaderboard ──────────────────────────────────────────────────────────────

async def get_leaderboard(
    db: AsyncSession,
    tenant_id: int,
    period: str = "week",  # week | month | all_time
    limit: int = 20,
) -> list[dict]:
    """
    Compute real-time leaderboard for the tenant.
    Rank by: points + (avg_score * 0.1) + (total_rehearsals * 2)
    """
    result = await db.execute(
        select(UserStats)
        .where(UserStats.tenant_id == tenant_id)
        .order_by(
            (UserStats.total_points +
             func.coalesce(UserStats.avg_rehearsal_score * 0.1, 0) +
             UserStats.total_rehearsals * 2
             ).desc()
        )
        .limit(limit)
    )
    stats_list = result.scalars().all()

    leaderboard = []
    for rank, stats in enumerate(stats_list, start=1):
        # Get user display info
        from app.models.user import PcUser
        user_res = await db.execute(select(PcUser).where(PcUser.id == stats.user_id))
        user = user_res.scalar_one_or_none()

        leaderboard.append({
            "rank": rank,
            "user_id": stats.user_id,
            "display_name": (user.full_name or user.email.split("@")[0] if user else f"用户{stats.user_id}"),
            "avatar": getattr(user, "avatar_url", None),
            "total_points": stats.total_points or 0,
            "total_rehearsals": stats.total_rehearsals or 0,
            "best_score": float(stats.best_rehearsal_score) if stats.best_rehearsal_score else 0,
            "avg_score": float(stats.avg_rehearsal_score) if stats.avg_rehearsal_score else 0,
            "current_streak": stats.current_streak or 0,
            "total_achievements": stats.total_achievements or 0,
        })
    return leaderboard


async def get_user_achievements(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
) -> list[dict]:
    """Get all achievements for a user, with earn status."""
    # All active achievements
    all_ach_result = await db.execute(
        select(Achievement).where(Achievement.is_active == True).order_by(Achievement.id)
    )
    all_achievements = all_ach_result.scalars().all()

    # Earned by this user
    earned_result = await db.execute(
        select(UserAchievement)
        .where(UserAchievement.user_id == user_id, UserAchievement.tenant_id == tenant_id)
    )
    earned_map = {ua.achievement_id: ua for ua in earned_result.scalars().all()}

    return [
        {
            "id": ach.id,
            "code": ach.code,
            "name": ach.name,
            "description": ach.description,
            "icon_emoji": ach.icon_emoji,
            "category": ach.category,
            "points": ach.points,
            "earned": ach.id in earned_map,
            "earned_at": earned_map[ach.id].earned_at.isoformat() if ach.id in earned_map else None,
        }
        for ach in all_achievements
    ]


async def get_user_stats(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
) -> dict:
    """Get stats for a user."""
    stats = await _get_or_create_stats(db, tenant_id, user_id)
    await db.commit()
    return {
        "total_rehearsals": stats.total_rehearsals or 0,
        "total_practice_sessions": stats.total_practice_sessions or 0,
        "total_qa_sessions": stats.total_qa_sessions or 0,
        "best_rehearsal_score": float(stats.best_rehearsal_score) if stats.best_rehearsal_score else 0,
        "avg_rehearsal_score": float(stats.avg_rehearsal_score) if stats.avg_rehearsal_score else 0,
        "current_streak": stats.current_streak or 0,
        "longest_streak": stats.longest_streak or 0,
        "total_points": stats.total_points or 0,
        "total_achievements": stats.total_achievements or 0,
        "last_activity_at": stats.last_activity_at.isoformat() if stats.last_activity_at else None,
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _badge_dict(ach: Achievement) -> dict:
    return {
        "code": ach.code,
        "name": ach.name,
        "description": ach.description,
        "icon_emoji": ach.icon_emoji,
        "points": ach.points,
    }
