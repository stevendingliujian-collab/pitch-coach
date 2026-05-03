"""
A/B Test API
============
Endpoints for frontend variant assignment and conversion tracking.
Also includes admin endpoints for viewing results.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ab_test import AbTest
from app.models.user import User
from app.services import ab_test_service

router = APIRouter(prefix="/ab-tests", tags=["ab-tests"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class VariantAssignment(BaseModel):
    test_name: str
    variant: str


class BatchAssignResponse(BaseModel):
    assignments: dict[str, str]   # {test_name: variant}


class RecordEventRequest(BaseModel):
    test_name: str
    event_type: str = "conversion"
    meta: dict | None = None


class VariantStats(BaseModel):
    variant: str
    assigned: int
    conversions: int
    conversion_rate: float


class TestResultsResponse(BaseModel):
    test_name: str
    variants: list[VariantStats]


class AbTestInfo(BaseModel):
    name: str
    description: str | None
    variants: list[str]
    is_active: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/assign", response_model=BatchAssignResponse)
async def assign_variants(
    tests: str = Query(..., description="Comma-separated test names, e.g. pricing_layout,onboarding_steps"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return variant assignments for the current user across one or more tests.
    Idempotent — repeated calls return the same variants.
    """
    test_names = [t.strip() for t in tests.split(",") if t.strip()]
    if not test_names:
        raise HTTPException(400, "No test names provided")
    if len(test_names) > 20:
        raise HTTPException(400, "Too many tests in one request (max 20)")

    assignments = await ab_test_service.batch_get_variants(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        test_names=test_names,
        db=db,
    )
    return BatchAssignResponse(assignments=assignments)


@router.post("/events", status_code=204)
async def record_event(
    body: RecordEventRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a conversion or interaction event for a given test."""
    await ab_test_service.record_event(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        test_name=body.test_name,
        event_type=body.event_type,
        db=db,
        meta=body.meta,
    )


@router.get("/active", response_model=list[AbTestInfo])
async def list_active_tests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all currently active A/B tests (useful for frontend to know which tests to enroll in)."""
    result = await db.execute(
        select(AbTest).where(AbTest.is_active == True).order_by(AbTest.name)
    )
    tests = result.scalars().all()
    return [
        AbTestInfo(
            name=t.name,
            description=t.description,
            variants=t.variants or [],
            is_active=t.is_active,
        )
        for t in tests
    ]


@router.get("/{test_name}/results", response_model=TestResultsResponse)
async def get_results(
    test_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get per-variant assignment counts and conversion rates.
    Useful for the internal dashboard / operations team.
    """
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(403, "Only admins and managers can view A/B test results")
    return await ab_test_service.get_test_results(test_name, db)
