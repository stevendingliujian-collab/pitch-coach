"""
Dashboard API — team-level analytics for the F6 看板.

Provides:
  GET /dashboard/overview   — summary stats (tasks, rehearsals, avg score, top members)
  GET /dashboard/trend      — daily rehearsal counts + avg score for the past N days
  GET /dashboard/members    — per-member rehearsal stats
  GET /dashboard/tasks      — task readiness leaderboard
"""
from __future__ import annotations

from datetime import datetime, timedelta, date
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.rehearsal import Rehearsal
from app.models.pitch_task import PitchTask

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return headline KPIs for the tenant."""
    tenant_id = current_user.tenant_id

    # Total active tasks
    tasks_res = await db.execute(
        select(func.count(PitchTask.id)).where(
            PitchTask.tenant_id == tenant_id,
            PitchTask.status != 3,
        )
    )
    total_tasks = tasks_res.scalar_one() or 0

    # Total scored rehearsals this month
    year_month = datetime.utcnow().strftime("%Y-%m")
    month_start = datetime.strptime(year_month + "-01", "%Y-%m-%d")

    reh_res = await db.execute(
        select(
            func.count(Rehearsal.id).label("count"),
            func.avg(Rehearsal.total_score).label("avg_score"),
            func.max(Rehearsal.total_score).label("best_score"),
        ).where(
            Rehearsal.tenant_id == tenant_id,
            Rehearsal.status >= 3,
            Rehearsal.created_at >= month_start,
        )
    )
    row = reh_res.one()
    month_rehearsals = row.count or 0
    avg_score = round(float(row.avg_score), 1) if row.avg_score else None
    best_score = round(float(row.best_score), 1) if row.best_score else None

    # All-time totals
    all_reh_res = await db.execute(
        select(func.count(Rehearsal.id)).where(
            Rehearsal.tenant_id == tenant_id,
            Rehearsal.status >= 3,
        )
    )
    total_rehearsals = all_reh_res.scalar_one() or 0

    # Tasks with bid_date in the next 7 days
    now = datetime.utcnow()
    upcoming_res = await db.execute(
        select(func.count(PitchTask.id)).where(
            PitchTask.tenant_id == tenant_id,
            PitchTask.status != 3,
            PitchTask.bid_date >= now.date(),
            PitchTask.bid_date <= (now + timedelta(days=7)).date(),
        )
    )
    upcoming_bids = upcoming_res.scalar_one() or 0

    return {
        "total_tasks": total_tasks,
        "total_rehearsals": total_rehearsals,
        "month_rehearsals": month_rehearsals,
        "avg_score": avg_score,
        "best_score": best_score,
        "upcoming_bids_7d": upcoming_bids,
        "year_month": year_month,
    }


@router.get("/trend")
async def get_trend(
    days: int = Query(default=30, ge=7, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return daily rehearsal counts and average scores for the past N days."""
    tenant_id = current_user.tenant_id
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Rehearsal.created_at).label("day"),
            func.count(Rehearsal.id).label("count"),
            func.avg(Rehearsal.total_score).label("avg_score"),
        ).where(
            Rehearsal.tenant_id == tenant_id,
            Rehearsal.status >= 3,
            Rehearsal.created_at >= since,
        ).group_by(func.date(Rehearsal.created_at))
        .order_by(func.date(Rehearsal.created_at))
    )
    rows = result.all()

    # Fill in missing days with 0
    date_map: dict[str, dict] = {}
    for row in rows:
        day_str = row.day.isoformat() if isinstance(row.day, date) else str(row.day)
        date_map[day_str] = {
            "date": day_str,
            "rehearsals": row.count,
            "avg_score": round(float(row.avg_score), 1) if row.avg_score else None,
        }

    points = []
    cur = since.date()
    end = datetime.utcnow().date()
    while cur <= end:
        ds = cur.isoformat()
        points.append(date_map.get(ds, {"date": ds, "rehearsals": 0, "avg_score": None}))
        cur += timedelta(days=1)

    return {"days": days, "points": points}


@router.get("/members")
async def get_member_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return per-member rehearsal stats for the tenant."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(
            Rehearsal.user_id,
            func.count(Rehearsal.id).label("rehearsal_count"),
            func.avg(Rehearsal.total_score).label("avg_score"),
            func.max(Rehearsal.total_score).label("best_score"),
            func.max(Rehearsal.created_at).label("last_rehearsed"),
        ).where(
            Rehearsal.tenant_id == tenant_id,
            Rehearsal.status >= 3,
        ).group_by(Rehearsal.user_id)
        .order_by(func.avg(Rehearsal.total_score).desc().nulls_last())
    )
    rows = result.all()

    # Fetch user names
    user_ids = [r.user_id for r in rows]
    users_res = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    user_map = {u.id: u for u in users_res.scalars().all()}

    stats = []
    for i, row in enumerate(rows):
        u = user_map.get(row.user_id)
        stats.append({
            "rank": i + 1,
            "user_id": row.user_id,
            "name": (u.name or u.email or f"用户{row.user_id}") if u else f"用户{row.user_id}",
            "rehearsal_count": row.rehearsal_count,
            "avg_score": round(float(row.avg_score), 1) if row.avg_score else None,
            "best_score": round(float(row.best_score), 1) if row.best_score else None,
            "last_rehearsed": row.last_rehearsed.isoformat() if row.last_rehearsed else None,
        })

    return stats


@router.get("/tasks")
async def get_task_readiness(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all active tasks with rehearsal stats, ordered by bid_date."""
    tenant_id = current_user.tenant_id

    tasks_res = await db.execute(
        select(PitchTask).where(
            PitchTask.tenant_id == tenant_id,
            PitchTask.status != 3,
        ).order_by(PitchTask.bid_date.asc().nulls_last())
    )
    tasks = tasks_res.scalars().all()

    if not tasks:
        return []

    task_ids = [t.id for t in tasks]
    agg_res = await db.execute(
        select(
            Rehearsal.pitch_task_id,
            func.count(Rehearsal.id).label("rehearsal_count"),
            func.avg(Rehearsal.total_score).label("avg_score"),
            func.max(Rehearsal.total_score).label("best_score"),
            func.max(Rehearsal.created_at).label("last_rehearsed"),
        ).where(
            Rehearsal.pitch_task_id.in_(task_ids),
            Rehearsal.status >= 3,
        ).group_by(Rehearsal.pitch_task_id)
    )

    agg_map: dict[int, Any] = {}
    for row in agg_res.all():
        agg_map[row.pitch_task_id] = row

    now = datetime.utcnow().date()
    result = []
    for task in tasks:
        agg = agg_map.get(task.id)
        rc = agg.rehearsal_count if agg else 0
        bs = float(agg.best_score) if agg and agg.best_score else None
        avg = float(agg.avg_score) if agg and agg.avg_score else None
        last = agg.last_rehearsed.isoformat() if agg and agg.last_rehearsed else None

        # Readiness 0-100
        count_contrib = min(rc, 5) / 5 * 40
        score_contrib = (bs or 0) / 100 * 60 if bs else 0
        readiness = round(count_contrib + score_contrib)

        # Days until bid
        days_left: int | None = None
        if task.bid_date:
            days_left = (task.bid_date - now).days

        result.append({
            "task_id": task.id,
            "name": task.name,
            "customer_name": task.customer_name,
            "bid_date": task.bid_date.isoformat() if task.bid_date else None,
            "days_until_bid": days_left,
            "rehearsal_count": rc,
            "avg_score": round(avg, 1) if avg else None,
            "best_score": round(bs, 1) if bs else None,
            "readiness_score": readiness,
            "last_rehearsed": last,
        })

    return result


@router.get("/roi")
async def get_roi(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    ROI 计算器 — 量化述标训练价值：
    - 总练习时长（分钟）
    - 得分提升（首次 vs 最近均值）
    - 赢单率（已知结果的任务中中标比例）
    - 已参与的述标金额（已中标任务预算合计）
    """
    tenant_id = current_user.tenant_id

    # ── 练习时长（所有已评分排练 audio_duration 秒求和）──────────────────────
    dur_res = await db.execute(
        select(func.sum(Rehearsal.audio_duration)).where(
            Rehearsal.tenant_id == tenant_id,
            Rehearsal.status >= 3,
        )
    )
    total_duration_sec = int(dur_res.scalar_one() or 0)
    total_practice_min = round(total_duration_sec / 60)

    # ── 得分提升（首次排练均分 vs 最近30天均分）───────────────────────────────
    # earliest 5 rehearsals
    first_res = await db.execute(
        select(func.avg(Rehearsal.total_score)).where(
            Rehearsal.tenant_id == tenant_id,
            Rehearsal.status >= 3,
            Rehearsal.total_score.isnot(None),
        ).order_by(Rehearsal.created_at.asc()).limit(5)
    )
    first_avg = float(first_res.scalar_one() or 0)

    # recent 30 days
    since_30 = datetime.utcnow() - timedelta(days=30)
    recent_res = await db.execute(
        select(func.avg(Rehearsal.total_score)).where(
            Rehearsal.tenant_id == tenant_id,
            Rehearsal.status >= 3,
            Rehearsal.total_score.isnot(None),
            Rehearsal.created_at >= since_30,
        )
    )
    recent_avg = float(recent_res.scalar_one() or 0)
    score_improvement = round(recent_avg - first_avg, 1) if first_avg > 0 else None

    # ── 赢单率 ──────────────────────────────────────────────────────────────
    outcome_res = await db.execute(
        select(
            PitchTask.result,
            func.count(PitchTask.id).label("cnt"),
        ).where(
            PitchTask.tenant_id == tenant_id,
            PitchTask.result.isnot(None),
        ).group_by(PitchTask.result)
    )
    outcome_counts: dict[int, int] = {}
    for row in outcome_res.all():
        outcome_counts[row.result] = row.cnt

    won_count = outcome_counts.get(1, 0)
    total_outcomes = sum(outcome_counts.values())
    win_rate = round(won_count / total_outcomes * 100) if total_outcomes > 0 else None

    # ── 已中标项目预算合计 ────────────────────────────────────────────────────
    budget_res = await db.execute(
        select(func.sum(PitchTask.budget)).where(
            PitchTask.tenant_id == tenant_id,
            PitchTask.result == 1,
            PitchTask.budget.isnot(None),
        )
    )
    won_budget_total = float(budget_res.scalar_one() or 0)

    # ── 总排练次数 ─────────────────────────────────────────────────────────────
    count_res = await db.execute(
        select(func.count(Rehearsal.id)).where(
            Rehearsal.tenant_id == tenant_id,
            Rehearsal.status >= 3,
        )
    )
    total_rehearsals = int(count_res.scalar_one() or 0)

    return {
        "total_practice_min": total_practice_min,
        "total_rehearsals": total_rehearsals,
        "score_improvement": score_improvement,
        "first_avg_score": round(first_avg, 1) if first_avg > 0 else None,
        "recent_avg_score": round(recent_avg, 1) if recent_avg > 0 else None,
        "win_rate": win_rate,
        "won_count": won_count,
        "total_outcomes": total_outcomes,
        "won_budget_total": round(won_budget_total / 10000, 1),  # convert to 万元
    }
