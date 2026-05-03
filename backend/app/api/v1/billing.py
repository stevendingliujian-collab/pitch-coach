"""
Billing API — subscription management + payment history.

NOTE: Payment is simulated (no real payment gateway integration yet).
      Real integration would add /billing/checkout to generate a payment
      link and /billing/webhook to handle callbacks from WeChat Pay / Alipay.
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.services.billing_service import (
    PLANS,
    get_plan_info,
    calculate_upgrade_proration,
    create_payment_record,
    activate_subscription,
    cancel_subscription,
    get_usage_summary,
)
from app.api.v1.subscription import _get_or_create as _get_or_create_sub

router = APIRouter(prefix="/billing", tags=["billing"])

# ── Schemas ────────────────────────────────────────────────────────────────

class UpgradeRequest(BaseModel):
    plan_type: str
    billing_cycle: str = "monthly"  # monthly | annual
    payment_method: str = "manual"


class PaymentResponse(BaseModel):
    id: int
    plan_type: str
    billing_cycle: str
    amount: float
    currency: str
    status: str
    payment_method: str
    description: str | None
    invoice_no: str | None
    period_start: datetime | None
    period_end: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingOverview(BaseModel):
    subscription: dict[str, Any]
    plan_info: dict[str, Any]
    usage: dict[str, Any]
    upcoming_renewal: dict[str, Any] | None


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/plans")
async def list_plans():
    """Return all available plans and pricing."""
    return {
        plan_id: {
            "id": plan_id,
            "name": info["name"],
            "monthly_price": float(info["monthly_price"]),
            "annual_price": float(info["annual_price"]),
            "max_users": info["max_users"],
            "features": info["features"],
        }
        for plan_id, info in PLANS.items()
    }


@router.get("/overview", response_model=BillingOverview)
async def get_billing_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return subscription status, usage stats, and upcoming renewal."""
    sub = await _get_or_create_sub(current_user.tenant_id, db)
    await db.commit()

    plan_info = get_plan_info(sub.plan_type)
    year_month = datetime.utcnow().strftime("%Y-%m")
    usage = await get_usage_summary(db, current_user.tenant_id, year_month)

    # Upcoming renewal
    renewal = None
    if sub.status == "active" and sub.expires_at:
        plan = get_plan_info(sub.plan_type)
        # Determine billing cycle from last payment
        last_pay = await db.execute(
            select(Payment)
            .where(Payment.tenant_id == current_user.tenant_id, Payment.status == "completed")
            .order_by(Payment.created_at.desc())
        )
        lp = last_pay.scalars().first()
        cycle = lp.billing_cycle if lp else "monthly"
        price = plan["annual_price"] if cycle == "annual" else plan["monthly_price"]
        renewal = {
            "date": sub.expires_at.date().isoformat(),
            "amount": float(price),
            "plan_name": plan["name"],
            "billing_cycle": cycle,
        }

    return BillingOverview(
        subscription={
            "status": sub.status,
            "plan_type": sub.plan_type,
            "is_active": sub.is_active,
            "effective_plan": sub.effective_plan,
            "trial_days_left": sub.trial_days_left,
            "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        },
        plan_info={
            "id": sub.plan_type,
            "name": plan_info["name"],
            "monthly_price": float(plan_info["monthly_price"]),
            "annual_price": float(plan_info["annual_price"]),
            "max_users": plan_info["max_users"],
        },
        usage={
            "year_month": year_month,
            **usage,
            "limits": {
                "ppt_uploads": None if sub.is_active else 3,
                "rehearsals": None if sub.is_active else 5,
                "narration_pages": None if sub.is_active else 3,
                "knowledge_docs": None if sub.is_active else 0,
            },
        },
        upcoming_renewal=renewal,
    )


@router.post("/upgrade")
async def upgrade_subscription(
    body: UpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate upgrading / purchasing a subscription.
    In production, this would return a payment URL instead.
    """
    if body.plan_type not in PLANS:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan_type}")
    if body.plan_type == "free":
        raise HTTPException(status_code=400, detail="Use /billing/cancel to downgrade to free")

    plan_info = get_plan_info(body.plan_type)
    amount = plan_info["annual_price"] if body.billing_cycle == "annual" else plan_info["monthly_price"]

    # Create payment record
    payment = await create_payment_record(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        plan_type=body.plan_type,
        amount=amount,
        billing_cycle=body.billing_cycle,
        payment_method=body.payment_method,
    )

    # Activate subscription
    sub = await _get_or_create_sub(current_user.tenant_id, db)
    sub = await activate_subscription(db, sub, body.plan_type, body.billing_cycle)

    await db.commit()
    await db.refresh(payment)

    return {
        "message": f"已成功升级至 {plan_info['name']}",
        "invoice_no": payment.invoice_no,
        "amount": float(payment.amount),
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
    }


@router.post("/cancel")
async def cancel_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel subscription at end of current period."""
    sub = await _get_or_create_sub(current_user.tenant_id, db)

    if sub.status not in ("active", "trial"):
        raise HTTPException(status_code=400, detail="没有可取消的有效订阅")

    sub = await cancel_subscription(db, sub)
    await db.commit()

    return {
        "message": "订阅将在当前计费周期结束后停止",
        "effective_date": sub.expires_at.isoformat() if sub.expires_at else "立即生效",
    }


@router.get("/payments", response_model=list[PaymentResponse])
async def list_payments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return payment history for the tenant."""
    result = await db.execute(
        select(Payment)
        .where(Payment.tenant_id == current_user.tenant_id)
        .order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()
    return [_pay_to_response(p) for p in payments]


@router.get("/invoice/{invoice_no}")
async def get_invoice(
    invoice_no: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return invoice details."""
    result = await db.execute(
        select(Payment).where(
            Payment.invoice_no == invoice_no,
            Payment.tenant_id == current_user.tenant_id,
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {
        **_pay_to_response(payment).model_dump(),
        "billed_to": current_user.name or current_user.email or "—",
        "tenant_id": current_user.tenant_id,
    }


# ── Helpers ────────────────────────────────────────────────────────────────

def _pay_to_response(p: Payment) -> PaymentResponse:
    return PaymentResponse(
        id=p.id,
        plan_type=p.plan_type,
        billing_cycle=p.billing_cycle,
        amount=float(p.amount),
        currency=p.currency,
        status=p.status,
        payment_method=p.payment_method,
        description=p.description,
        invoice_no=p.invoice_no,
        period_start=p.period_start,
        period_end=p.period_end,
        created_at=p.created_at,
    )
