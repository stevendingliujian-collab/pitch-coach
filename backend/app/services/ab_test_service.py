"""
A/B Testing Service
===================
Lightweight deterministic bucketing + event tracking.

Bucketing algorithm:
  hash(user_id + test_name) mod 100 → maps to a variant based on cumulative weights.

Example:
  variants = ["control", "variant_b"], weights = [50, 50]
  hash bucket 0-49 → "control", 50-99 → "variant_b"
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ab_test import AbTest, AbTestAssignment, AbTestEvent

logger = logging.getLogger(__name__)


def _bucket(user_id: int, test_name: str) -> int:
    """Deterministic 0-99 bucket for a (user, test) pair."""
    raw = f"{user_id}:{test_name}"
    digest = hashlib.md5(raw.encode()).hexdigest()
    return int(digest[:8], 16) % 100


def _pick_variant(bucket: int, variants: list[str], weights: list[int] | None) -> str:
    """Map bucket 0-99 to a variant using cumulative weights."""
    if not variants:
        return "control"
    if not weights or len(weights) != len(variants):
        # Equal split
        per_variant = 100 // len(variants)
        weights = [per_variant] * len(variants)
        weights[-1] = 100 - per_variant * (len(variants) - 1)

    cumulative = 0
    for variant, weight in zip(variants, weights):
        cumulative += weight
        if bucket < cumulative:
            return variant
    return variants[-1]


async def get_variant(
    user_id: int,
    tenant_id: int,
    test_name: str,
    db: AsyncSession,
) -> str | None:
    """
    Return the variant assigned to this user for `test_name`.
    Assigns (and persists) on first call; returns cached assignment thereafter.
    Returns None if the test doesn't exist or is inactive.
    """
    # Check cache first
    result = await db.execute(
        select(AbTestAssignment).where(
            AbTestAssignment.user_id == user_id,
            AbTestAssignment.test_name == test_name,
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment:
        return assignment.variant

    # Load test definition
    result = await db.execute(
        select(AbTest).where(AbTest.name == test_name, AbTest.is_active == True)
    )
    test = result.scalar_one_or_none()
    if not test:
        return None

    # Check date bounds
    now = datetime.utcnow()
    if test.start_date and now < test.start_date:
        return None
    if test.end_date and now > test.end_date:
        return None

    # Assign deterministically
    bucket = _bucket(user_id, test_name)
    variant = _pick_variant(bucket, test.variants or [], test.weights)

    assignment = AbTestAssignment(
        test_name=test_name,
        user_id=user_id,
        tenant_id=tenant_id,
        variant=variant,
    )
    db.add(assignment)
    try:
        await db.commit()
        await db.refresh(assignment)
    except Exception:
        await db.rollback()
        # Race condition — another request may have already inserted; re-fetch
        result = await db.execute(
            select(AbTestAssignment).where(
                AbTestAssignment.user_id == user_id,
                AbTestAssignment.test_name == test_name,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment:
            return assignment.variant
        return variant  # fallback

    return variant


async def batch_get_variants(
    user_id: int,
    tenant_id: int,
    test_names: list[str],
    db: AsyncSession,
) -> dict[str, str]:
    """Get variants for multiple tests in one call (fewer DB round-trips)."""
    out: dict[str, str] = {}
    for name in test_names:
        v = await get_variant(user_id, tenant_id, name, db)
        if v is not None:
            out[name] = v
    return out


async def record_event(
    user_id: int,
    tenant_id: int,
    test_name: str,
    event_type: str,
    db: AsyncSession,
    meta: dict | None = None,
) -> None:
    """Record a conversion/click/etc. event for result analysis."""
    # Look up variant
    result = await db.execute(
        select(AbTestAssignment).where(
            AbTestAssignment.user_id == user_id,
            AbTestAssignment.test_name == test_name,
        )
    )
    assignment = result.scalar_one_or_none()
    variant = assignment.variant if assignment else "unknown"

    event = AbTestEvent(
        test_name=test_name,
        user_id=user_id,
        tenant_id=tenant_id,
        variant=variant,
        event_type=event_type,
        meta=meta,
    )
    db.add(event)
    try:
        await db.commit()
    except Exception:
        logger.exception("Failed to record ab test event")
        await db.rollback()


async def get_test_results(
    test_name: str,
    db: AsyncSession,
) -> dict:
    """
    Return per-variant assignment counts + conversion counts.
    Conversion = event_type == "conversion".
    """
    from sqlalchemy import func

    # Assignment counts per variant
    assign_rows = await db.execute(
        select(AbTestAssignment.variant, func.count().label("assigned"))
        .where(AbTestAssignment.test_name == test_name)
        .group_by(AbTestAssignment.variant)
    )
    assign_map: dict[str, int] = {row.variant: row.assigned for row in assign_rows}

    # Conversion counts per variant
    conv_rows = await db.execute(
        select(AbTestEvent.variant, func.count().label("conversions"))
        .where(AbTestEvent.test_name == test_name, AbTestEvent.event_type == "conversion")
        .group_by(AbTestEvent.variant)
    )
    conv_map: dict[str, int] = {row.variant: row.conversions for row in conv_rows}

    variants = sorted(set(assign_map) | set(conv_map))
    stats = []
    for v in variants:
        assigned = assign_map.get(v, 0)
        conversions = conv_map.get(v, 0)
        stats.append({
            "variant": v,
            "assigned": assigned,
            "conversions": conversions,
            "conversion_rate": round(conversions / assigned * 100, 2) if assigned else 0.0,
        })

    return {
        "test_name": test_name,
        "variants": stats,
    }
