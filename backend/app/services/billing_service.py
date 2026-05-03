"""
Billing Service — subscription state machine + plan pricing.

State machine:
  free → trial (7 days, once) → expired
  free → active (paid)
  active → cancelled (takes effect at period end)
  active → active (renewal / upgrade)
  cancelled → free (on period end, or via downgrade)

Plan pricing (CNY):
  pro_10:   ¥399/月, ¥3192/年 (=¥266/月, ~¥319/月 as shown)
  pro_20:   ¥699/月, ¥5592/年
  elite_50: ¥999/月, ¥7992/年
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import secrets
import string
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.usage import UsageMeter

# ── Plan catalogue ──────────────────────────────────────────────────────────

PLANS: dict[str, dict] = {
    "free": {
        "name": "免费版",
        "monthly_price": Decimal("0"),
        "annual_price": Decimal("0"),
        "max_users": 1,
        "features": ["ppt_3/month", "rehearsal_5/month", "narration_3pages", "daily_practice"],
    },
    "pro_10": {
        "name": "专业版 (≤10人)",
        "monthly_price": Decimal("399"),
        "annual_price": Decimal("3192"),  # 399×12×0.8 ≈ 3830 → discount to 3192
        "max_users": 10,
        "features": ["ppt_unlimited", "rehearsal_unlimited", "narration_full",
                     "training", "rubric", "evaluator", "review", "knowledge_500mb"],
    },
    "pro_20": {
        "name": "专业版 (≤20人)",
        "monthly_price": Decimal("699"),
        "annual_price": Decimal("5592"),
        "max_users": 20,
        "features": ["ppt_unlimited", "rehearsal_unlimited", "narration_full",
                     "training", "rubric", "evaluator", "review", "knowledge_500mb"],
    },
    "elite_50": {
        "name": "旗舰版 (≤50人)",
        "monthly_price": Decimal("999"),
        "annual_price": Decimal("7992"),
        "max_users": 50,
        "features": ["all_pro", "post_mortem", "video_export", "knowledge_5gb", "open_api"],
    },
}


def get_plan_info(plan_type: str) -> dict:
    return PLANS.get(plan_type, PLANS["free"])


def calculate_upgrade_proration(
    current_plan: str,
    new_plan: str,
    days_used: int,
    billing_cycle: str = "monthly",
) -> Decimal:
    """
    Calculate proration credit when upgrading mid-cycle.
    Returns the net amount to charge (new - unused portion of old).
    """
    cycle_days = 365 if billing_cycle == "annual" else 30
    days_remaining = max(0, cycle_days - days_used)
    fraction = Decimal(str(days_remaining / cycle_days))

    old_info = get_plan_info(current_plan)
    new_info = get_plan_info(new_plan)

    if billing_cycle == "annual":
        old_monthly = old_info["annual_price"] / 12
        new_monthly = new_info["annual_price"] / 12
    else:
        old_monthly = old_info["monthly_price"]
        new_monthly = new_info["monthly_price"]

    credit = old_monthly * fraction
    charge = new_monthly - credit
    return max(Decimal("0"), charge.quantize(Decimal("0.01")))


def _generate_invoice_no() -> str:
    """Generate a unique invoice number like INV-20260504-A3B2."""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"INV-{date_str}-{suffix}"


async def create_payment_record(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    plan_type: str,
    amount: Decimal,
    billing_cycle: str = "monthly",
    payment_method: str = "manual",
    description: str | None = None,
) -> Payment:
    """Create a payment record and return it."""
    now = datetime.utcnow()
    if billing_cycle == "annual":
        period_end = now + timedelta(days=365)
    else:
        period_end = now + timedelta(days=30)

    payment = Payment(
        tenant_id=tenant_id,
        user_id=user_id,
        payment_method=payment_method,
        status="completed",  # simulated — real integration would start as "pending"
        plan_type=plan_type,
        billing_cycle=billing_cycle,
        amount=amount,
        description=description or f"{get_plan_info(plan_type)['name']} — {billing_cycle}",
        invoice_no=_generate_invoice_no(),
        period_start=now,
        period_end=period_end,
    )
    db.add(payment)
    await db.flush()
    return payment


async def activate_subscription(
    db: AsyncSession,
    subscription: Subscription,
    plan_type: str,
    billing_cycle: str = "monthly",
) -> Subscription:
    """Activate or upgrade a subscription after payment."""
    now = datetime.utcnow()
    days = 365 if billing_cycle == "annual" else 30

    subscription.status = "active"
    subscription.plan_type = plan_type
    subscription.activated_at = now
    subscription.expires_at = now + timedelta(days=days)
    subscription.updated_at = now
    return subscription


async def cancel_subscription(
    db: AsyncSession,
    subscription: Subscription,
) -> Subscription:
    """Cancel at end of current period."""
    now = datetime.utcnow()
    subscription.status = "cancelled"
    subscription.cancelled_at = now
    subscription.updated_at = now
    # Keeps expires_at → still active until period end
    return subscription


async def get_usage_summary(
    db: AsyncSession,
    tenant_id: int,
    year_month: str,
) -> dict[str, Any]:
    """Aggregate monthly usage across all users in the tenant."""
    result = await db.execute(
        select(UsageMeter).where(
            UsageMeter.tenant_id == tenant_id,
            UsageMeter.year_month == year_month,
        )
    )
    meters = result.scalars().all()

    totals: dict[str, int] = {
        "ppt_uploads": 0,
        "rehearsals": 0,
        "narration_pages": 0,
        "knowledge_docs": 0,
    }
    for m in meters:
        totals["ppt_uploads"] += m.ppt_uploads
        totals["rehearsals"] += m.rehearsals
        totals["narration_pages"] += m.narration_pages
        totals["knowledge_docs"] += m.knowledge_docs

    return totals
