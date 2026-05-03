"""Subscription API — 7-day trial + plan status."""
from __future__ import annotations

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.subscription import Subscription
from app.models.tenant import Tenant

router = APIRouter(prefix="/subscription", tags=["subscription"])

TRIAL_DAYS = 7


# ── Helpers ───────────────────────────────────────────────────────────────

async def _get_or_create(tenant_id: int, db: AsyncSession) -> Subscription:
    result = await db.execute(
        select(Subscription).where(Subscription.tenant_id == tenant_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(tenant_id=tenant_id, status="free", plan_type="free")
        db.add(sub)
        await db.flush()
    return sub


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("")
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return current tenant subscription state."""
    sub = await _get_or_create(current_user.tenant_id, db)
    await db.commit()
    return _serialize(sub)


@router.post("/trial/start")
async def start_trial(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Activate 7-day professional trial for the tenant (once per tenant)."""
    sub = await _get_or_create(current_user.tenant_id, db)

    if sub.status not in ("free",):
        raise HTTPException(400, detail="试用仅适用于免费版账户")
    if sub.trial_starts_at is not None:
        raise HTTPException(400, detail="该账户已使用过试用资格")

    now = datetime.utcnow()
    sub.status = "trial"
    sub.plan_type = "pro"
    sub.trial_starts_at = now
    sub.trial_ends_at = now + timedelta(days=TRIAL_DAYS)
    sub.updated_at = now

    # Keep tenant.plan_type in sync
    tenant = await db.get(Tenant, current_user.tenant_id)
    if tenant:
        tenant.plan_type = "pro"

    await db.commit()
    await db.refresh(sub)
    return _serialize(sub)


@router.get("/status")
async def get_plan_status(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Lightweight endpoint: just returns plan type for feature-gating."""
    sub = await _get_or_create(current_user.tenant_id, db)
    await db.commit()
    return {
        "plan": sub.effective_plan,
        "status": sub.status,
        "trial_days_left": sub.trial_days_left,
        "is_active": sub.is_active,
    }


@router.get("/usage")
async def get_usage_summary(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return current-month usage for the sidebar meter (pitch_tasks & rehearsals)."""
    from app.services.quota_service import get_usage_summary
    return await get_usage_summary(current_user, db)


def _serialize(sub: Subscription) -> dict:
    return {
        "id": sub.id,
        "tenant_id": sub.tenant_id,
        "status": sub.status,
        "plan_type": sub.plan_type,
        "is_active": sub.is_active,
        "effective_plan": sub.effective_plan,
        "trial_days_left": sub.trial_days_left,
        "trial_starts_at": sub.trial_starts_at.isoformat() if sub.trial_starts_at else None,
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        "created_at": sub.created_at.isoformat(),
    }
