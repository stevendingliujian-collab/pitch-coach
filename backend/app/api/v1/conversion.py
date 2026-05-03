"""Conversion trigger API — lets the frontend check triggers and record events."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.conversion_service import ConversionService, track_event

router = APIRouter(prefix="/conversion", tags=["conversion"])


class CheckTriggerResponse(BaseModel):
    should_show: bool
    trigger_id: str
    label: str
    message: str


class TrackEventRequest(BaseModel):
    event_name: str
    properties: dict | None = None


@router.get("/trigger/{trigger_id}", response_model=CheckTriggerResponse)
async def check_trigger(
    trigger_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check whether an upgrade trigger should be shown to the current user."""
    result = await ConversionService.check_trigger(
        trigger_id=trigger_id,
        user=current_user,
        db=db,
    )
    return CheckTriggerResponse(**result)


@router.post("/trigger/{trigger_id}/dismissed", status_code=204)
async def dismiss_trigger(
    trigger_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record that the user dismissed this trigger's banner."""
    await ConversionService.record_dismissed(trigger_id, current_user, db)


@router.post("/trigger/{trigger_id}/converted", status_code=204)
async def convert_trigger(
    trigger_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record that the user clicked 'Upgrade' from this trigger."""
    await ConversionService.record_converted(trigger_id, current_user, db)


@router.post("/events", status_code=204)
async def track_analytics_event(
    body: TrackEventRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Track a frontend analytics event (fire-and-forget)."""
    await track_event(body.event_name, current_user, db, properties=body.properties)
