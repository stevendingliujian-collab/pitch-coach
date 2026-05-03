from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.pitch_task import PitchTask
from app.models.rehearsal import Rehearsal
from app.schemas.pitch_task import PitchTaskCreate, PitchTaskUpdate, PitchTaskResponse
from app.services.quota_service import increment_usage
from app.services.conversion_service import track_event

router = APIRouter(prefix="/pitch-tasks", tags=["pitch-tasks"])


def _compute_readiness(rehearsal_count: int, best_score: float | None) -> int:
    """Readiness 0-100: weighted by rehearsal count (40%) and best score (60%)."""
    if rehearsal_count == 0:
        return 0
    count_contrib = min(rehearsal_count, 5) / 5 * 40
    score_contrib = (best_score or 0) / 100 * 60 if best_score else 0
    return round(count_contrib + score_contrib)


@router.get("", response_model=list[PitchTaskResponse])
async def list_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PitchTask)
        .where(PitchTask.tenant_id == current_user.tenant_id, PitchTask.status != 3)
        .order_by(PitchTask.bid_date.asc().nulls_last(), PitchTask.created_at.desc())
    )
    tasks = result.scalars().all()
    if not tasks:
        return []

    # Compute rehearsal aggregates per task
    task_ids = [t.id for t in tasks]
    agg = await db.execute(
        select(
            Rehearsal.pitch_task_id,
            func.count(Rehearsal.id).label("rehearsal_count"),
            func.max(Rehearsal.total_score).label("best_score"),
        )
        .where(
            Rehearsal.pitch_task_id.in_(task_ids),
            Rehearsal.status >= 3,  # scored or beyond
        )
        .group_by(Rehearsal.pitch_task_id)
    )
    agg_map: dict[int, dict] = {}
    for row in agg.all():
        agg_map[row.pitch_task_id] = {
            "rehearsal_count": row.rehearsal_count,
            "best_score": float(row.best_score) if row.best_score else None,
        }

    # Annotate tasks with computed fields
    responses = []
    for task in tasks:
        a = agg_map.get(task.id, {})
        rc = a.get("rehearsal_count", 0)
        bs = a.get("best_score")
        responses.append(PitchTaskResponse(
            id=task.id,
            name=task.name,
            customer_name=task.customer_name,
            customer_industry=task.customer_industry,
            budget=task.budget,
            bid_date=task.bid_date,
            bid_time_limit=task.bid_time_limit,
            status=task.status,
            result=task.result,
            owner_id=task.owner_id,
            rehearsal_count=rc,
            best_score=bs,
            readiness_score=_compute_readiness(rc, bs),
            created_at=task.created_at.date() if task.created_at else None,
        ))
    return responses


@router.post("", response_model=PitchTaskResponse, status_code=201)
async def create_task(
    body: PitchTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = PitchTask(
        tenant_id=current_user.tenant_id,
        owner_id=current_user.id,
        **body.model_dump(exclude_none=False),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    # Track usage (gate already checked by FeatureGateMiddleware)
    await increment_usage("ppt_uploads", current_user, db, meta={"task_id": task.id})
    await track_event("ppt_uploaded", current_user, db,
                      properties={"task_id": task.id, "task_name": task.name})
    await db.commit()
    return task


@router.get("/{task_id}", response_model=PitchTaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, current_user.tenant_id, db)
    return task


@router.patch("/{task_id}", response_model=PitchTaskResponse)
async def update_task(
    task_id: int,
    body: PitchTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, current_user.tenant_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def archive_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, current_user.tenant_id, db)
    task.status = 3  # archived
    await db.commit()


async def _get_task_or_404(task_id: int, tenant_id: int, db: AsyncSession) -> PitchTask:
    result = await db.execute(
        select(PitchTask).where(PitchTask.id == task_id, PitchTask.tenant_id == tenant_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
