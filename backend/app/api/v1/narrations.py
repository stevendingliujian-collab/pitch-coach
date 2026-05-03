"""F2 AI 示范讲解 API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.narration import DemoNarration
from app.models.pitch_plan import PitchPlan
from app.services.tts_adapter import VOICE_PRESETS, DEFAULT_VOICE_ID
from app.core.storage import get_presigned_download_url

router = APIRouter(prefix="/narrations", tags=["narrations"])


class GenerateNarrationRequest(BaseModel):
    voice_id: str = DEFAULT_VOICE_ID
    voice_name: str = "专业男声"
    speed: float = 1.0


class NarrationResponse(BaseModel):
    id: int
    plan_id: int
    voice_id: str
    voice_name: str | None
    speed: float
    status: int
    # 0=pending 1=generating_scripts 2=synthesizing 3=merging 4=ready 5=error
    status_label: str
    page_audios: list | None = None
    total_audio_url: str | None = None
    total_duration_sec: int | None = None
    error_msg: str | None = None

    model_config = {"from_attributes": True}


_STATUS_LABELS = {
    0: "pending",
    1: "generating_scripts",
    2: "synthesizing",
    3: "merging",
    4: "ready",
    5: "error",
}


def _enrich(n: DemoNarration) -> dict:
    d = {
        "id": n.id,
        "plan_id": n.plan_id,
        "voice_id": n.voice_id,
        "voice_name": n.voice_name,
        "speed": n.speed,
        "status": n.status,
        "status_label": _STATUS_LABELS.get(n.status, "unknown"),
        "page_audios": n.page_audios,
        "total_audio_url": None,
        "total_duration_sec": n.total_duration_sec,
        "error_msg": n.error_msg,
    }
    if n.total_audio_url:
        try:
            d["total_audio_url"] = get_presigned_download_url(n.total_audio_url)
        except Exception:
            d["total_audio_url"] = n.total_audio_url
    # Sign individual page audio URLs too
    if n.page_audios:
        signed_pages = []
        for p in n.page_audios:
            p2 = dict(p)
            if p2.get("audio_url"):
                try:
                    p2["audio_url"] = get_presigned_download_url(p2["audio_url"])
                except Exception:
                    pass
            signed_pages.append(p2)
        d["page_audios"] = signed_pages
    return d


@router.post("/{plan_id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_narration(
    plan_id: int,
    req: GenerateNarrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Trigger AI narration generation for a plan."""
    plan = await db.get(PitchPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403)
    if plan.status not in (1, 2):  # must be generated or manually edited
        raise HTTPException(status_code=400, detail="Plan not ready (generate plan first)")

    # Cancel any in-flight narrations for this plan
    existing = await db.execute(
        select(DemoNarration)
        .where(DemoNarration.plan_id == plan_id)
        .order_by(DemoNarration.id.desc())
        .limit(1)
    )
    prev = existing.scalar_one_or_none()
    if prev and prev.status in (0, 1, 2, 3):
        raise HTTPException(
            status_code=409,
            detail="Narration generation already in progress",
        )

    narration = DemoNarration(
        tenant_id=current_user.tenant_id,
        plan_id=plan_id,
        voice_id=req.voice_id,
        voice_name=req.voice_name,
        speed=req.speed,
        status=0,
        created_by=current_user.id,
    )
    db.add(narration)
    await db.commit()
    await db.refresh(narration)

    from app.workers.tasks import generate_narration_task
    generate_narration_task.delay(narration.id)

    return {"narration_id": narration.id, "status": "accepted"}


@router.get("/{plan_id}/latest")
async def get_latest_narration(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the latest narration record for a plan."""
    plan = await db.get(PitchPlan, plan_id)
    if not plan or plan.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404)

    result = await db.execute(
        select(DemoNarration)
        .where(DemoNarration.plan_id == plan_id)
        .order_by(DemoNarration.id.desc())
        .limit(1)
    )
    narration = result.scalar_one_or_none()
    if not narration:
        raise HTTPException(status_code=404, detail="No narration found")

    return _enrich(narration)


@router.get("/{plan_id}/list")
async def list_narrations(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all narrations for a plan (newest first)."""
    plan = await db.get(PitchPlan, plan_id)
    if not plan or plan.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404)

    result = await db.execute(
        select(DemoNarration)
        .where(DemoNarration.plan_id == plan_id)
        .order_by(DemoNarration.id.desc())
    )
    narrations = result.scalars().all()
    return [_enrich(n) for n in narrations]


@router.get("/voices")
async def list_voices(_=Depends(get_current_user)):
    """List available TTS voice presets."""
    return [
        {"id": vid, "name": name}
        for name, vid in VOICE_PRESETS.items()
    ]
