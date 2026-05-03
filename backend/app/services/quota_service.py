"""
Quota Service — free-tier usage metering and limit enforcement.

Free plan limits (per calendar month, per user):
  - ppt_uploads:      3
  - rehearsals:       5
  - narration_pages:  3  (only first 3 pages of AI demo narration)
  - knowledge_docs:   0  (feature disabled on free)

The service is intentionally lightweight — no Redis, pure DB, optimistic approach.
Heavy contention is not a concern at this stage.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.user import User
from app.models.usage import UsageMeter, UsageEvent

# ---------------------------------------------------------------------------
# Free-tier quota table
# ---------------------------------------------------------------------------

FREE_LIMITS: dict[str, int | None] = {
    "ppt_uploads":     3,
    "rehearsals":      5,
    "narration_pages": 3,    # first 3 pages only; gated per-page in narration API
    "knowledge_docs":  0,    # blocked entirely
}

# Map feature key → human-readable label for error messages
FEATURE_LABELS: dict[str, str] = {
    "ppt_uploads":     "PPT 上传（免费版 3 份/月）",
    "rehearsals":      "对练排练（免费版 5 次/月）",
    "narration_pages": "AI 示范讲解（免费版前 3 页）",
    "knowledge_docs":  "知识库上传",
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _year_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


async def get_meter(user: User, db: AsyncSession) -> UsageMeter:
    """Return (or create) the current-month meter row for this user."""
    ym = _year_month()
    meter = await db.execute(
        select(UsageMeter).where(
            UsageMeter.user_id == user.id,
            UsageMeter.year_month == ym,
        )
    )
    row = meter.scalar_one_or_none()
    if row:
        return row

    # Upsert: race-safe via INSERT … ON CONFLICT DO NOTHING
    stmt = (
        pg_insert(UsageMeter)
        .values(tenant_id=user.tenant_id, user_id=user.id, year_month=ym)
        .on_conflict_do_nothing(constraint="uk_user_month")
    )
    await db.execute(stmt)
    await db.flush()

    result = await db.execute(
        select(UsageMeter).where(
            UsageMeter.user_id == user.id,
            UsageMeter.year_month == ym,
        )
    )
    return result.scalar_one()


async def check_quota(
    feature: str,
    user: User,
    db: AsyncSession,
    *,
    plan_type: str = "free",
) -> tuple[bool, int, int | None]:
    """
    Check whether the user still has quota for *feature*.

    Returns (allowed, current_usage, limit).
    - allowed=True  → proceed
    - allowed=False → quota exceeded, raise 402 upstream
    - limit=None    → unlimited (paid plans)
    """
    if plan_type != "free":
        # Paid plans: always allowed (quota checks happen at billing layer later)
        current = getattr(await get_meter(user, db), feature, 0)
        return True, current, None

    limit = FREE_LIMITS.get(feature)
    if limit is None:
        return True, 0, None  # unknown feature → pass through

    meter = await get_meter(user, db)
    current = getattr(meter, feature, 0)
    return current < limit, current, limit


async def increment_usage(
    feature: str,
    user: User,
    db: AsyncSession,
    *,
    delta: int = 1,
    meta: Optional[dict] = None,
) -> None:
    """
    Atomically increment the meter counter and append an audit event.
    Call this *after* the operation succeeds.
    """
    ym = _year_month()

    # Upsert meter row and increment
    col = getattr(UsageMeter, feature, None)
    if col is None:
        return  # unknown feature, skip

    stmt = (
        pg_insert(UsageMeter)
        .values(
            tenant_id=user.tenant_id,
            user_id=user.id,
            year_month=ym,
            **{feature: delta},
        )
        .on_conflict_do_update(
            constraint="uk_user_month",
            set_={feature: col + delta, "updated_at": datetime.utcnow()},
        )
    )
    await db.execute(stmt)

    # Append audit event
    event = UsageEvent(
        tenant_id=user.tenant_id,
        user_id=user.id,
        feature=feature,
        year_month=ym,
        delta=delta,
        meta=meta,
    )
    db.add(event)
    await db.flush()


async def get_usage_summary(user: User, db: AsyncSession) -> dict:
    """Return current-month usage dict with limits and percentages."""
    meter = await get_meter(user, db)
    result = {}
    for feature, limit in FREE_LIMITS.items():
        used = getattr(meter, feature, 0)
        result[feature] = {
            "used": used,
            "limit": limit,
            "pct": round(used / limit * 100) if limit else 0,
            "label": FEATURE_LABELS.get(feature, feature),
        }
    return result
