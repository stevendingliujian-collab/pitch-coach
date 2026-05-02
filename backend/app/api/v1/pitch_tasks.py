from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.pitch_task import PitchTask
from app.schemas.pitch_task import PitchTaskCreate, PitchTaskUpdate, PitchTaskResponse

router = APIRouter(prefix="/pitch-tasks", tags=["pitch-tasks"])


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
    return result.scalars().all()


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
