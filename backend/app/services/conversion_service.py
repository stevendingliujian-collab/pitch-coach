"""
Conversion engine — T1-T9 upgrade trigger logic.

Each trigger has:
  - max_shows = 1     (each trigger shown at most once per user)
  - cooldown = 30 days  (if somehow re-triggered, honour cooldown)

Trigger IDs from the product plan:
  T1  AI示范播到第3页结束          → 免费→专业
  T2  月内第5次排练完成             → 免费→专业
  T3  用户点击「评分表对标」         → 免费→专业
  T4  用户尝试邀请团队成员           → 免费→专业
  T5  排练3次后展示进步曲线          → 免费→专业
  T6  用户点击「评委模拟」           → 免费→专业
  T7  专业版点击AI复盘/场景引擎      → 专业→旗舰
  T8  专业版连续3次排练≥85分        → 专业→旗舰
  T9  述标日期前7天设置              → 免费→专业

Usage:
    result = await ConversionService.check_trigger(
        trigger_id="T1",
        user=current_user,
        db=db,
        meta={"page": 3},
    )
    # result: {"should_show": bool, "trigger_id": str, "label": str, "message": str}
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.conversion import UpgradeTrigger, TriggerEvent, AnalyticsEvent
from app.models.user import User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Trigger registry
# ---------------------------------------------------------------------------

TRIGGERS: dict[str, dict[str, Any]] = {
    "T1": {
        "label": "AI示范讲解",
        "message": "解锁专业版，获得完整 PPT 逐页 AI 示范讲解，立即提升述标表现！",
        "target": "free→pro",
        "max_shows": 1,
        "cooldown_days": 30,
    },
    "T2": {
        "label": "排练次数",
        "message": "本月排练已达 5 次，升级专业版享受无限次排练！",
        "target": "free→pro",
        "max_shows": 1,
        "cooldown_days": 30,
    },
    "T3": {
        "label": "评分表对标",
        "message": "评分表对标功能可帮你精准命中评委打分项，升级专业版立即解锁！",
        "target": "free→pro",
        "max_shows": 1,
        "cooldown_days": 30,
    },
    "T4": {
        "label": "团队协作",
        "message": "邀请团队成员共同练习，专业版支持团队协作与经理审核！",
        "target": "free→pro",
        "max_shows": 1,
        "cooldown_days": 30,
    },
    "T5": {
        "label": "练习进步曲线",
        "message": "你已完成 3 次排练，看看你的进步吧！升级专业版可查看完整趋势分析。",
        "target": "free→pro",
        "max_shows": 1,
        "cooldown_days": 30,
    },
    "T6": {
        "label": "评委模拟",
        "message": "AI 评委模拟可帮你预判真实评委问题，升级专业版立即开始！",
        "target": "free→pro",
        "max_shows": 1,
        "cooldown_days": 30,
    },
    "T7": {
        "label": "AI复盘助手",
        "message": "AI 复盘助手和动态场景引擎仅旗舰版可用，解锁全部智能分析！",
        "target": "pro→premium",
        "max_shows": 1,
        "cooldown_days": 30,
    },
    "T8": {
        "label": "旗舰版升级",
        "message": "你已连续 3 次排练得分 ≥85 分，已达专业水准！旗舰版提供更深度的智能训练。",
        "target": "pro→premium",
        "max_shows": 1,
        "cooldown_days": 30,
    },
    "T9": {
        "label": "述标倒计时",
        "message": "距述标仅剩 7 天！升级专业版，启动 AI 强化训练模式，全力备战！",
        "target": "free→pro",
        "max_shows": 1,
        "cooldown_days": 7,  # shorter cooldown for urgency trigger
    },
}


class ConversionService:
    """Check whether a trigger should be shown; record show/dismiss/convert events."""

    @staticmethod
    async def check_trigger(
        trigger_id: str,
        user: User,
        db: AsyncSession,
        meta: dict | None = None,
    ) -> dict[str, Any]:
        """
        Determine if the trigger should be shown to this user.

        Returns:
            {
                "should_show": bool,
                "trigger_id": str,
                "label": str,
                "message": str,
            }
        """
        trigger_def = TRIGGERS.get(trigger_id)
        if not trigger_def:
            return {"should_show": False, "trigger_id": trigger_id, "label": "", "message": ""}

        max_shows = trigger_def["max_shows"]
        cooldown_days = trigger_def["cooldown_days"]

        # Load or create the upgrade_trigger record
        result = await db.execute(
            select(UpgradeTrigger).where(
                UpgradeTrigger.user_id == user.id,
                UpgradeTrigger.trigger_id == trigger_id,
            )
        )
        record: UpgradeTrigger | None = result.scalar_one_or_none()

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if record:
            # Already shown max_shows times → skip
            if record.show_count >= max_shows:
                return {"should_show": False, "trigger_id": trigger_id,
                        "label": trigger_def["label"], "message": trigger_def["message"]}

            # Still in cooldown window → skip
            if record.last_shown_at:
                cooldown_end = record.last_shown_at + timedelta(days=cooldown_days)
                if now < cooldown_end:
                    return {"should_show": False, "trigger_id": trigger_id,
                            "label": trigger_def["label"], "message": trigger_def["message"]}

        # Should show — upsert the trigger record
        stmt = pg_insert(UpgradeTrigger).values(
            tenant_id=user.tenant_id,
            user_id=user.id,
            trigger_id=trigger_id,
            show_count=1,
            max_shows=max_shows,
            converted=False,
            last_shown_at=now,
        ).on_conflict_do_update(
            index_elements=["user_id", "trigger_id"],
            set_={
                "show_count": UpgradeTrigger.show_count + 1,
                "last_shown_at": now,
            },
        )
        await db.execute(stmt)

        # Log trigger event
        db.add(TriggerEvent(
            tenant_id=user.tenant_id,
            user_id=user.id,
            trigger_id=trigger_id,
            event_type="shown",
            meta=meta,
        ))
        await db.commit()

        return {
            "should_show": True,
            "trigger_id": trigger_id,
            "label": trigger_def["label"],
            "message": trigger_def["message"],
        }

    @staticmethod
    async def record_dismissed(
        trigger_id: str,
        user: User,
        db: AsyncSession,
    ) -> None:
        """Record that the user dismissed the upgrade banner for this trigger."""
        db.add(TriggerEvent(
            tenant_id=user.tenant_id,
            user_id=user.id,
            trigger_id=trigger_id,
            event_type="dismissed",
        ))
        await db.commit()

    @staticmethod
    async def record_converted(
        trigger_id: str,
        user: User,
        db: AsyncSession,
    ) -> None:
        """Record that the user clicked 'Upgrade' from this trigger."""
        result = await db.execute(
            select(UpgradeTrigger).where(
                UpgradeTrigger.user_id == user.id,
                UpgradeTrigger.trigger_id == trigger_id,
            )
        )
        record = result.scalar_one_or_none()
        if record:
            record.converted = True

        db.add(TriggerEvent(
            tenant_id=user.tenant_id,
            user_id=user.id,
            trigger_id=trigger_id,
            event_type="converted",
        ))
        await db.commit()


# ---------------------------------------------------------------------------
# Analytics helpers
# ---------------------------------------------------------------------------

async def track_event(
    event_name: str,
    user: User,
    db: AsyncSession,
    properties: dict | None = None,
) -> None:
    """
    Append an analytics event. Fire-and-forget; errors are swallowed.

    Core events:
        user_registered, ppt_uploaded, plan_generated,
        rehearsal_completed, daily_practice_done, upgrade_clicked
    """
    try:
        db.add(AnalyticsEvent(
            tenant_id=user.tenant_id,
            user_id=user.id,
            event_name=event_name,
            properties=properties,
        ))
        await db.commit()
    except Exception as exc:
        logger.warning("Failed to track event %s: %s", event_name, exc)
        await db.rollback()
