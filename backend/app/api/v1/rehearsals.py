import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import get_presigned_upload_url, get_presigned_download_url
from app.models.user import User
from app.models.pitch_task import PitchTask
from app.models.rehearsal import Rehearsal
from app.schemas.rehearsal import (
    StartRehearsalRequest, StartRehearsalResponse,
    CompleteRehearsalRequest, RehearsalStatusResponse,
    RehearsalReportResponse, RehearsalListItem,
    PageTiming, FillerWordDetail, PageScore,
)
from app.workers.tasks import score_rehearsal_task
from app.services.quota_service import increment_usage
from app.services.conversion_service import track_event

router = APIRouter(prefix="/rehearsals", tags=["rehearsals"])


@router.post("/start", response_model=StartRehearsalResponse, status_code=201)
async def start_rehearsal(
    body: StartRehearsalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create rehearsal record and return presigned audio upload URL."""
    task = await db.get(PitchTask, body.pitch_task_id)
    if not task or task.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "pitch task not found")

    object_key = (
        f"{current_user.tenant_id}/pitch-coach/rehearsals/"
        f"{body.pitch_task_id}/{uuid.uuid4().hex}.webm"
    )
    upload_url = get_presigned_upload_url(object_key, expires_seconds=7200)

    rehearsal = Rehearsal(
        tenant_id=current_user.tenant_id,
        pitch_task_id=body.pitch_task_id,
        plan_id=body.plan_id,
        user_id=current_user.id,
        audio_url=object_key,
        audio_duration=0,
        status=0,
    )
    db.add(rehearsal)
    await db.commit()
    await db.refresh(rehearsal)

    # Track usage (gate already checked by FeatureGateMiddleware)
    await increment_usage("rehearsals", current_user, db, meta={"rehearsal_id": rehearsal.id})
    await track_event("rehearsal_started", current_user, db,
                      properties={"rehearsal_id": rehearsal.id, "pitch_task_id": body.pitch_task_id})
    await db.commit()

    return StartRehearsalResponse(
        rehearsal_id=rehearsal.id,
        upload_url=upload_url,
        object_key=object_key,
    )


@router.post("/{rehearsal_id}/complete", response_model=RehearsalStatusResponse)
async def complete_rehearsal(
    rehearsal_id: int,
    body: CompleteRehearsalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark audio as uploaded; start async scoring pipeline."""
    rehearsal = await _get_rehearsal(rehearsal_id, current_user, db)

    rehearsal.audio_url = body.object_key
    rehearsal.audio_duration = body.audio_duration
    rehearsal.page_timings = [pt.model_dump() for pt in body.page_timings]
    rehearsal.status = 1  # transcribing

    await db.commit()
    await db.refresh(rehearsal)

    # Enqueue async scoring
    score_rehearsal_task.delay(rehearsal.id)

    return RehearsalStatusResponse(rehearsal_id=rehearsal.id, status=rehearsal.status)


@router.get("/{rehearsal_id}/status", response_model=RehearsalStatusResponse)
async def get_rehearsal_status(
    rehearsal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rehearsal = await _get_rehearsal(rehearsal_id, current_user, db)
    return RehearsalStatusResponse(
        rehearsal_id=rehearsal.id,
        status=rehearsal.status,
        total_score=float(rehearsal.total_score) if rehearsal.total_score else None,
        fluency_score=_dim(rehearsal, "fluency"),
        rate_score=_dim(rehearsal, "rate"),
        timing_score=_dim(rehearsal, "timing"),
    )


@router.get("/{rehearsal_id}/report", response_model=RehearsalReportResponse)
async def get_rehearsal_report(
    rehearsal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rehearsal = await _get_rehearsal(rehearsal_id, current_user, db)
    if rehearsal.status < 3:
        raise HTTPException(409, "scoring not complete yet")

    audio_url = get_presigned_download_url(rehearsal.audio_url, expires_seconds=3600)
    dims = rehearsal.dimension_scores or {}

    filler_detail = [
        FillerWordDetail(**d) for d in (rehearsal.filler_word_detail or [])
    ]
    page_scores = [PageScore(**p) for p in (rehearsal.page_scores or [])]
    page_timings = [PageTiming(**p) for p in (rehearsal.page_timings or [])]

    return RehearsalReportResponse(
        rehearsal_id=rehearsal.id,
        pitch_task_id=rehearsal.pitch_task_id,
        status=rehearsal.status,
        audio_url=audio_url,
        audio_duration=rehearsal.audio_duration,
        total_score=float(rehearsal.total_score) if rehearsal.total_score else None,
        fluency_score=dims.get("fluency"),
        rate_score=dims.get("rate"),
        timing_score=dims.get("timing"),
        filler_count=rehearsal.filler_word_count,
        filler_detail=filler_detail,
        chars_per_min=dims.get("chars_per_min"),
        total_duration_sec=dims.get("total_duration_sec"),
        improvement_tips=rehearsal.improvement_tips or [],
        page_scores=page_scores,
        page_timings=page_timings,
        created_at=rehearsal.created_at,
    )


@router.get("/task/{pitch_task_id}", response_model=list[RehearsalListItem])
async def list_rehearsals(
    pitch_task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Rehearsal)
        .where(
            Rehearsal.pitch_task_id == pitch_task_id,
            Rehearsal.tenant_id == current_user.tenant_id,
        )
        .order_by(Rehearsal.created_at.desc())
    )
    rehearsals = result.scalars().all()
    return [
        RehearsalListItem(
            rehearsal_id=r.id,
            pitch_task_id=r.pitch_task_id,
            status=r.status,
            total_score=float(r.total_score) if r.total_score else None,
            audio_duration=r.audio_duration,
            created_at=r.created_at,
        )
        for r in rehearsals
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_rehearsal(rehearsal_id: int, user: User, db: AsyncSession) -> Rehearsal:
    r = await db.get(Rehearsal, rehearsal_id)
    if not r or r.tenant_id != user.tenant_id:
        raise HTTPException(404, "rehearsal not found")
    return r


def _dim(rehearsal: Rehearsal, key: str) -> float | None:
    if rehearsal.dimension_scores:
        v = rehearsal.dimension_scores.get(key)
        return float(v) if v is not None else None
    return None
