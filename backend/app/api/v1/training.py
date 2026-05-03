"""F3 训练计划 API: 跟读/背诵模式 + 艾宾浩斯复习排程"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.training import TrainingPlan, TrainingSession
from app.models.pitch_plan import PlanPage
from app.models.narration import DemoNarration
from app.models.user import User
from app.services.training_service import (
    get_or_create_plan,
    get_today_plan,
    score_follow_read,
    score_recitation,
    generate_ebbinghaus_schedule,
)

router = APIRouter(prefix="/training", tags=["training"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class PlanResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    pitch_task_id: int
    plan_id: Optional[int]
    first_practice_date: Optional[str]
    bid_date: Optional[str]
    schedule_dates: Optional[list[str]]
    created_at: str

    model_config = {"from_attributes": True}


class SessionRequest(BaseModel):
    plan_id: int
    mode: str              # "follow" | "recite"
    page_number: int
    transcript: str        # ASR output from client
    audio_url: Optional[str] = None
    duration_sec: int = 60


class SessionResponse(BaseModel):
    id: int
    plan_id: int
    mode: str
    page_number: int
    total_score: Optional[float]
    dimension_scores: Optional[dict]
    feedback: Optional[list[str]]
    practice_date: str
    created_at: str

    model_config = {"from_attributes": True}


def _plan_to_response(plan: TrainingPlan) -> PlanResponse:
    return PlanResponse(
        id=plan.id,
        tenant_id=plan.tenant_id,
        user_id=plan.user_id,
        pitch_task_id=plan.pitch_task_id,
        plan_id=plan.plan_id,
        first_practice_date=plan.first_practice_date.isoformat() if plan.first_practice_date else None,
        bid_date=plan.bid_date.isoformat() if plan.bid_date else None,
        schedule_dates=plan.schedule_dates,
        created_at=plan.created_at.isoformat() if plan.created_at else "",
    )


def _session_to_response(sess: TrainingSession) -> SessionResponse:
    return SessionResponse(
        id=sess.id,
        plan_id=sess.plan_id,
        mode=sess.mode,
        page_number=sess.page_number,
        total_score=float(sess.total_score) if sess.total_score is not None else None,
        dimension_scores=sess.dimension_scores,
        feedback=sess.feedback,
        practice_date=sess.practice_date.isoformat(),
        created_at=sess.created_at.isoformat() if sess.created_at else "",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_plan(
    pitch_task_id: int = Query(...),
    plan_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get or create a training plan for the current user + pitch task.
    Returns the existing plan if one already exists.
    """
    plan = await get_or_create_plan(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        pitch_task_id=pitch_task_id,
        plan_id=plan_id,
        db=db,
    )
    return _plan_to_response(plan)


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(
    pitch_task_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List training plans for the current user."""
    q = select(TrainingPlan).where(
        TrainingPlan.user_id == current_user.id,
        TrainingPlan.tenant_id == current_user.tenant_id,
    )
    if pitch_task_id:
        q = q.where(TrainingPlan.pitch_task_id == pitch_task_id)
    q = q.order_by(TrainingPlan.created_at.desc())

    result = await db.execute(q)
    plans = result.scalars().all()
    return [_plan_to_response(p) for p in plans]


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(TrainingPlan, plan_id)
    if not plan or plan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Training plan not found")
    return _plan_to_response(plan)


@router.get("/today", response_model=list[dict])
async def today_practice(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all training plans that have today scheduled (due for practice)."""
    return await get_today_plan(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        db=db,
    )


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def submit_session(
    req: SessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a completed follow-read or recitation session for scoring.

    The client should:
    1. Record audio
    2. Call ASR (or pass raw transcript)
    3. POST transcript + metadata here
    """
    plan = await db.get(TrainingPlan, req.plan_id)
    if not plan or plan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Training plan not found")

    if req.mode not in ("follow", "recite"):
        raise HTTPException(status_code=422, detail="mode must be 'follow' or 'recite'")

    # Load plan page for reference data
    page_result = await db.execute(
        select(PlanPage).where(
            PlanPage.plan_id == plan.plan_id,
            PlanPage.page_number == req.page_number,
        )
    )
    plan_page = page_result.scalar_one_or_none()
    talking_points: list[str] = plan_page.talking_points or [] if plan_page else []

    # Get reference script from demo narration (if exists)
    reference_script = ""
    reference_duration_sec = req.duration_sec  # fallback

    if plan.plan_id:
        narr_result = await db.execute(
            select(DemoNarration)
            .where(DemoNarration.plan_id == plan.plan_id, DemoNarration.status == 4)
            .order_by(DemoNarration.id.desc())
            .limit(1)
        )
        narration = narr_result.scalar_one_or_none()
        if narration and narration.page_audios:
            for pa in narration.page_audios:
                if pa.get("page_number") == req.page_number:
                    reference_script = pa.get("script", "")
                    reference_duration_sec = pa.get("duration_sec", req.duration_sec)
                    break

    # If no demo script, fall back to talking points joined
    if not reference_script and talking_points:
        reference_script = "。".join(talking_points)

    # Score based on mode
    if req.mode == "follow":
        score_result = score_follow_read(
            user_transcript=req.transcript,
            reference_script=reference_script,
            user_duration_sec=req.duration_sec,
            reference_duration_sec=reference_duration_sec,
        )
    else:  # recite
        score_result = score_recitation(
            user_transcript=req.transcript,
            talking_points=talking_points,
            reference_script=reference_script,
            user_duration_sec=req.duration_sec,
        )

    session = TrainingSession(
        plan_id=req.plan_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        pitch_task_id=plan.pitch_task_id,
        mode=req.mode,
        page_number=req.page_number,
        audio_url=req.audio_url,
        transcript=req.transcript,
        total_score=score_result["total_score"],
        dimension_scores=score_result["dimension_scores"],
        feedback=score_result["feedback"],
        practice_date=date.today(),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return _session_to_response(session)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    plan_id: Optional[int] = Query(None),
    pitch_task_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List practice sessions for the current user."""
    q = select(TrainingSession).where(
        TrainingSession.user_id == current_user.id,
        TrainingSession.tenant_id == current_user.tenant_id,
    )
    if plan_id:
        q = q.where(TrainingSession.plan_id == plan_id)
    if pitch_task_id:
        q = q.where(TrainingSession.pitch_task_id == pitch_task_id)
    q = q.order_by(TrainingSession.created_at.desc()).limit(100)

    result = await db.execute(q)
    sessions = result.scalars().all()
    return [_session_to_response(s) for s in sessions]


@router.get("/schedule/preview", response_model=list[str])
async def preview_schedule(
    first_date: str = Query(..., description="YYYY-MM-DD"),
    bid_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    """Preview Ebbinghaus schedule without creating a plan (useful for UI)."""
    try:
        first = date.fromisoformat(first_date)
        bid = date.fromisoformat(bid_date) if bid_date else None
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD")

    return generate_ebbinghaus_schedule(first, bid)
