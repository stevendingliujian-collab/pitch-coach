"""
Quota Service — feature-gate usage metering and limit enforcement.

Quotas are loaded from feature_registry.yaml (in the backend root directory).
Fallback hardcoded defaults are used if the file is missing.

The service is intentionally lightweight — no Redis, pure DB, optimistic approach.
Heavy contention is not a concern at this stage.
"""
from __future__ import annotations
import os
from datetime import datetime
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.user import User
from app.models.usage import UsageMeter, UsageEvent


# ---------------------------------------------------------------------------
# Load feature registry from YAML (with hardcoded fallback)
# ---------------------------------------------------------------------------

def _load_registry() -> dict:
    """Load feature_registry.yaml. Falls back to hardcoded defaults on error."""
    registry_path = os.path.join(
        os.path.dirname(__file__),  # app/services/
        "..", "..",                  # → backend/
        "feature_registry.yaml",
    )
    try:
        import yaml  # type: ignore
        with open(os.path.normpath(registry_path), "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("features", {})
    except Exception:
        return {}


_REGISTRY: dict = _load_registry()


def _get_plan_limit(feature: str, plan: str) -> int | None:
    """Return the quota limit for feature+plan from registry. None = unlimited."""
    feat = _REGISTRY.get(feature)
    if not feat:
        # Unknown feature: fallback hardcoded limits
        return _FALLBACK_FREE.get(feature) if plan == "free" else None
    return feat.get("plans", {}).get(plan)


# Hardcoded fallback (used when YAML is absent or feature not in registry)
_FALLBACK_FREE: dict[str, int | None] = {
    "ppt_uploads":     3,
    "rehearsals":      5,
    "narration_pages": 3,
    "knowledge_docs":  0,
}

# Build FEATURE_LABELS and FREE_LIMITS from registry (for backward compat)
FEATURE_LABELS: dict[str, str] = {
    k: v.get("label", k)
    for k, v in _REGISTRY.items()
} if _REGISTRY else {
    "ppt_uploads":     "PPT 上传（免费版 3 份/月）",
    "rehearsals":      "对练排练（免费版 5 次/月）",
    "narration_pages": "AI 示范讲解（免费版前 3 页）",
    "knowledge_docs":  "知识库上传",
}

FREE_LIMITS: dict[str, int | None] = {
    k: _get_plan_limit(k, "free")
    for k in (list(_REGISTRY.keys()) if _REGISTRY else _FALLBACK_FREE.keys())
}

# ---------------------------------------------------------------------------
# Gated routes derived from registry (used by FeatureGateMiddleware)
# ---------------------------------------------------------------------------

def get_gated_routes() -> list[tuple[str, str, str, str]]:
    """
    Return list of (method, path_prefix, feature_key, trigger_id) tuples
    for routes that should be quota-gated by the middleware.
    """
    routes = []
    for feature_key, spec in _REGISTRY.items():
        method = spec.get("gated_method", "POST")
        path = spec.get("gated_path", "")
        trigger = spec.get("trigger_id", "T2")
        if path:
            routes.append((method, path, feature_key, trigger))
    return routes

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
    limit = _get_plan_limit(feature, plan_type)

    if limit is None:
        # Unlimited for this plan
        current = getattr(await get_meter(user, db), feature, 0) or 0
        return True, current, None

    meter = await get_meter(user, db)
    current = getattr(meter, feature, 0) or 0
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
