"""
F10 游戏化 API

端点：
- GET  /gamification/achievements          当前用户所有徽章（含未解锁）
- GET  /gamification/stats                 当前用户统计数据
- GET  /gamification/leaderboard           租户排行榜
- GET  /gamification/streak                连胜火焰信息
- POST /gamification/achievements/check    手动触发徽章检查（管理员用）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import PcUser
from app.models.gamification import UserStats
from app.services.gamification_service import (
    get_user_achievements,
    get_user_stats,
    get_leaderboard,
)

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/achievements")
async def list_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """获取当前用户所有徽章（含已解锁和未解锁）"""
    return await get_user_achievements(db, current_user.tenant_id, current_user.id)


@router.get("/stats")
async def user_stats(
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """获取当前用户游戏化统计数据"""
    return await get_user_stats(db, current_user.tenant_id, current_user.id)


@router.get("/leaderboard")
async def leaderboard(
    period: str = "week",
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """
    获取租户排行榜

    period: week | month | all_time
    """
    if period not in ("week", "month", "all_time"):
        period = "week"
    board = await get_leaderboard(db, current_user.tenant_id, period=period)

    # Find current user rank
    my_rank = next((item["rank"] for item in board if item["user_id"] == current_user.id), None)

    return {
        "period": period,
        "leaderboard": board,
        "my_rank": my_rank,
        "total_participants": len(board),
    }


@router.get("/streak")
async def get_streak(
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """获取连胜状态（用于首页火焰展示）"""
    result = await db.execute(
        select(UserStats).where(UserStats.user_id == current_user.id)
    )
    stats = result.scalar_one_or_none()

    current = stats.current_streak if stats else 0
    longest = stats.longest_streak if stats else 0

    # Streak fire level
    if current >= 20:
        fire_level = 3  # 🔥🔥🔥
    elif current >= 10:
        fire_level = 2  # 🔥🔥
    elif current >= 3:
        fire_level = 1  # 🔥
    else:
        fire_level = 0

    return {
        "current_streak": current,
        "longest_streak": longest,
        "fire_level": fire_level,
        "fire_emoji": "🔥" * fire_level if fire_level > 0 else "",
        "message": _streak_message(current),
    }


def _streak_message(streak: int) -> str:
    if streak >= 20:
        return f"🏆 传奇！连续 {streak} 次得分≥75，你是团队最强！"
    elif streak >= 10:
        return f"🔥 惊人！连续 {streak} 次高分，继续保持！"
    elif streak >= 5:
        return f"🎯 连续 {streak} 次高分，你正在高速进步！"
    elif streak >= 3:
        return f"⬆️ 连续 {streak} 次高分，好势头！"
    elif streak == 1:
        return "👍 好的开始！保持连胜冲击五连胜徽章！"
    else:
        return "💪 加油，继续练习，积累连胜！"
