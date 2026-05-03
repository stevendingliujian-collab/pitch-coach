"""
站内通知 API

按重要性实时计算通知项，无单独表，从现有数据聚合：
1. 述标 48h 倒计时（bid_date 距今 ≤ 2 天）
2. 待审核排练（经理角色：Certification.status == 0 且 rehearsal.status == 4）
3. 审核结果（普通用户：自己的 Certification 更新为 1/2 但 24h 内）
4. 日常练习未完成（当天无 DailyPracticeLog.status==1）
"""
from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import PcUser
from app.models.pitch_task import PitchTask
from app.models.rehearsal import Rehearsal
from app.models.review import Certification
from app.models.daily_practice import DailyPracticeLog

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Return in-app notifications for the current user."""
    items: list[dict[str, Any]] = []
    today = date.today()
    now = datetime.utcnow()

    # ── 1. 述标 48h 倒计时 ────────────────────────────────────────────────────
    deadline_48h = today + timedelta(days=2)
    bid_res = await db.execute(
        select(PitchTask).where(
            PitchTask.tenant_id == current_user.tenant_id,
            PitchTask.status != 3,
            PitchTask.bid_date >= today,
            PitchTask.bid_date <= deadline_48h,
        ).order_by(PitchTask.bid_date.asc())
    )
    for task in bid_res.scalars().all():
        days_left = (task.bid_date - today).days
        items.append({
            "type": "bid_countdown",
            "level": "urgent" if days_left == 0 else "warning",
            "title": f"述标倒计时：{'今天' if days_left == 0 else f'{days_left}天后'}",
            "message": f"「{task.name}」{f'今天' if days_left == 0 else f'还有 {days_left} 天'}述标，记得准备！",
            "task_id": task.id,
            "task_name": task.name,
            "bid_date": task.bid_date.isoformat(),
            "action_url": f"/projects/{task.id}?tab=readiness",
        })

    # ── 2. 经理待审核（role = manager/admin） ─────────────────────────────────
    if current_user.role in ("manager", "admin"):
        # Find rehearsals submitted for review (status=4) with pending certification
        pending_certs_res = await db.execute(
            select(
                Certification.id,
                Certification.pitch_task_id,
                Certification.user_id,
                Certification.rehearsal_id,
                PitchTask.name.label("task_name"),
            ).join(
                PitchTask, Certification.pitch_task_id == PitchTask.id
            ).where(
                Certification.tenant_id == current_user.tenant_id,
                Certification.status == 0,  # pending
            ).order_by(Certification.created_at.asc()).limit(10)
        )
        for row in pending_certs_res.all():
            items.append({
                "type": "review_pending",
                "level": "info",
                "title": "待审核排练",
                "message": f"「{row.task_name}」有排练等待您审核",
                "task_id": row.pitch_task_id,
                "task_name": row.task_name,
                "rehearsal_id": row.rehearsal_id,
                "action_url": f"/projects/{row.pitch_task_id}?tab=review",
            })

    # ── 3. 自己审核结果（24h内新审核通知） ────────────────────────────────────
    since_24h = now - timedelta(hours=24)
    my_cert_res = await db.execute(
        select(
            Certification.status,
            Certification.pitch_task_id,
            Certification.certified_at,
            PitchTask.name.label("task_name"),
        ).join(
            PitchTask, Certification.pitch_task_id == PitchTask.id
        ).where(
            Certification.tenant_id == current_user.tenant_id,
            Certification.user_id == current_user.id,
            Certification.status.in_([1, 2]),  # passed or rejected
            Certification.certified_at >= since_24h,
        )
    )
    for row in my_cert_res.all():
        passed = row.status == 1
        items.append({
            "type": "certification_result",
            "level": "success" if passed else "warning",
            "title": f"审核结果：{'通过 ✅' if passed else '需改进 ⚠️'}",
            "message": f"「{row.task_name}」排练审核{'已通过' if passed else '需要改进'}",
            "task_id": row.pitch_task_id,
            "task_name": row.task_name,
            "action_url": f"/projects/{row.pitch_task_id}?tab=review",
        })

    # ── 4. 今日练习未完成提醒 ────────────────────────────────────────────────
    today_log_res = await db.execute(
        select(DailyPracticeLog).where(
            DailyPracticeLog.user_id == current_user.id,
            DailyPracticeLog.practice_date == today,
            DailyPracticeLog.status == 1,
        ).limit(1)
    )
    if not today_log_res.scalar_one_or_none():
        items.append({
            "type": "daily_practice_reminder",
            "level": "info",
            "title": "今日微练习",
            "message": "今天还没完成每日微练习，保持连续打卡！",
            "action_url": "/daily-practice",
        })

    return items
