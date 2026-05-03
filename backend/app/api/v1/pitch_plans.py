import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import get_presigned_upload_url, upload_bytes, get_presigned_download_url
from app.core.config import get_settings
from app.models.user import User
from app.models.pitch_task import PitchTask
from app.models.pitch_plan import PitchPlan, PlanPage
from app.schemas.pitch_plan import (
    PitchPlanResponse, PlanPageResponse, PlanPageUpdate,
    GeneratePlanRequest, RegeneratePlanRequest,
)

settings = get_settings()
router = APIRouter(prefix="/pitch-plans", tags=["pitch-plans"])

ALLOWED_EXTENSIONS = {".pptx", ".pdf"}
MAX_SIZE_BYTES = settings.max_ppt_size_mb * 1024 * 1024


@router.post("/upload-url")
async def get_upload_url(
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """Return a pre-signed MinIO upload URL for direct browser upload."""
    ext = _validate_extension(filename)
    object_key = f"{current_user.tenant_id}/pitch-coach/ppts/{uuid.uuid4().hex}{ext}"
    url = get_presigned_upload_url(object_key, expires_seconds=3600)
    return {"upload_url": url, "object_key": object_key}


@router.post("/generate", status_code=202)
async def generate_plan(
    body: GeneratePlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a PitchPlan record and enqueue the generation task."""
    task_result = await db.execute(
        select(PitchTask).where(
            PitchTask.id == body.pitch_task_id,
            PitchTask.tenant_id == current_user.tenant_id,
        )
    )
    pitch_task = task_result.scalar_one_or_none()
    if not pitch_task:
        raise HTTPException(status_code=404, detail="Pitch task not found")

    plan = PitchPlan(
        tenant_id=current_user.tenant_id,
        pitch_task_id=body.pitch_task_id,
        ppt_file_id=body.ppt_file_id,
        ppt_file_name=body.ppt_file_name,
        bid_requirements=body.bid_requirements or pitch_task.bid_requirements,
        bid_time_limit=body.bid_time_limit or pitch_task.bid_time_limit or 30,
        customer_name=pitch_task.customer_name,
        customer_industry=pitch_task.customer_industry,
        project_budget=pitch_task.budget,
        competitor_info=pitch_task.competitor_info,
        status=0,
        created_by=current_user.id,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    from app.workers.tasks import generate_plan_task
    generate_plan_task.delay(plan.id)

    return {"plan_id": plan.id, "status": "generating", "estimated_seconds": 60}


@router.get("/{plan_id}", response_model=PitchPlanResponse)
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await _get_plan_or_404(plan_id, current_user.tenant_id, db)

    # Refresh thumbnail URLs (signed, 30-min expiry)
    for page in plan.pages:
        if page.page_thumbnail_url:
            try:
                page.page_thumbnail_url = get_presigned_download_url(page.page_thumbnail_url)
            except Exception:
                pass

    return plan


@router.get("/by-task/{task_id}", response_model=list[PitchPlanResponse])
async def list_plans_by_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PitchPlan)
        .options(selectinload(PitchPlan.pages))
        .where(
            PitchPlan.pitch_task_id == task_id,
            PitchPlan.tenant_id == current_user.tenant_id,
        )
        .order_by(PitchPlan.version.desc(), PitchPlan.id.desc())
    )
    plans = result.scalars().all()
    for plan in plans:
        for page in plan.pages:
            if page.page_thumbnail_url:
                try:
                    page.page_thumbnail_url = get_presigned_download_url(page.page_thumbnail_url)
                except Exception:
                    pass
    return plans


@router.put("/{plan_id}/pages/{page_number}", response_model=PlanPageResponse)
async def update_page(
    plan_id: int,
    page_number: int,
    body: PlanPageUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_plan_or_404(plan_id, current_user.tenant_id, db)
    result = await db.execute(
        select(PlanPage).where(PlanPage.plan_id == plan_id, PlanPage.page_number == page_number)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(page, field, value)
    page.is_manually_edited = True

    # Mark plan as user-edited
    plan_result = await db.execute(select(PitchPlan).where(PitchPlan.id == plan_id))
    plan = plan_result.scalar_one()
    if plan.status == 1:
        plan.status = 2

    await db.commit()
    await db.refresh(page)
    return page


@router.post("/{plan_id}/regenerate", status_code=202)
async def regenerate_plan(
    plan_id: int,
    body: RegeneratePlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await _get_plan_or_404(plan_id, current_user.tenant_id, db)
    plan.status = 0  # back to generating
    await db.commit()

    from app.workers.tasks import generate_plan_task
    generate_plan_task.delay(plan.id)

    return {"plan_id": plan_id, "status": "generating", "estimated_seconds": 60}


async def _get_plan_or_404(plan_id: int, tenant_id: int, db: AsyncSession) -> PitchPlan:
    result = await db.execute(
        select(PitchPlan)
        .options(selectinload(PitchPlan.pages))
        .where(PitchPlan.id == plan_id, PitchPlan.tenant_id == tenant_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def _validate_extension(filename: str) -> str:
    from pathlib import Path
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Use: {ALLOWED_EXTENSIONS}")
    return ext
