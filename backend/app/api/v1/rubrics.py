from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Any
from decimal import Decimal
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.rubric import ScoringRubric, RubricScore
from app.models.rehearsal import Rehearsal
from app.services.rubric_engine import (
    get_preset_templates,
    compute_rubric_total,
    score_rehearsal_against_rubric,
)

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class RubricItemSchema(BaseModel):
    id: str
    category: str
    item: str
    max_score: float
    weight: float = 0.0
    description: str = ""


class RubricCreate(BaseModel):
    name: str
    description: str | None = None
    items: list[RubricItemSchema]
    industry: str | None = None
    template_type: str | None = None


class RubricUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    items: list[RubricItemSchema] | None = None
    industry: str | None = None


class RubricResponse(BaseModel):
    id: int
    name: str
    description: str | None
    source_type: str
    items: list[Any]
    total_max_score: float | None
    industry: str | None
    template_type: str | None
    is_template: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RubricScoreResponse(BaseModel):
    id: int
    rubric_id: int
    rehearsal_id: int
    scores: list[Any]
    total_score: float | None
    coverage_percent: float | None
    coverage_detail: list[Any] | None
    improvement_suggestions: list[Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Preset templates (public) ─────────────────────────────────────────────────

@router.get("/templates")
async def list_preset_templates():
    """Return built-in rubric templates (no auth required)."""
    return get_preset_templates()


@router.post("/templates/{template_type}/import", response_model=RubricResponse, status_code=201)
async def import_preset_template(
    template_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Copy a preset template into the tenant's rubric library."""
    templates = get_preset_templates()
    tmpl = next((t for t in templates if t["template_type"] == template_type), None)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    rubric = ScoringRubric(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        name=tmpl["name"],
        description=tmpl.get("description"),
        source_type="template",
        items=tmpl["items"],
        total_max_score=Decimal(str(tmpl.get("total_max_score", 100))),
        industry=tmpl.get("industry"),
        template_type=template_type,
        is_template=False,
    )
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)
    return _to_response(rubric)


# ── Tenant rubrics CRUD ────────────────────────────────────────────────────────

@router.get("", response_model=list[RubricResponse])
async def list_rubrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScoringRubric)
        .where(ScoringRubric.tenant_id == current_user.tenant_id)
        .order_by(ScoringRubric.created_at.desc())
    )
    rubrics = result.scalars().all()
    return [_to_response(r) for r in rubrics]


@router.post("", response_model=RubricResponse, status_code=201)
async def create_rubric(
    body: RubricCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = [item.model_dump() for item in body.items]
    total = compute_rubric_total(items)
    rubric = ScoringRubric(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        name=body.name,
        description=body.description,
        source_type="manual",
        items=items,
        total_max_score=Decimal(str(total)),
        industry=body.industry,
        template_type=body.template_type,
        is_template=False,
    )
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)
    return _to_response(rubric)


@router.get("/{rubric_id}", response_model=RubricResponse)
async def get_rubric(
    rubric_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rubric = await _get_rubric_or_404(rubric_id, current_user.tenant_id, db)
    return _to_response(rubric)


@router.patch("/{rubric_id}", response_model=RubricResponse)
async def update_rubric(
    rubric_id: int,
    body: RubricUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rubric = await _get_rubric_or_404(rubric_id, current_user.tenant_id, db)
    if body.name is not None:
        rubric.name = body.name
    if body.description is not None:
        rubric.description = body.description
    if body.industry is not None:
        rubric.industry = body.industry
    if body.items is not None:
        items = [item.model_dump() for item in body.items]
        rubric.items = items
        rubric.total_max_score = Decimal(str(compute_rubric_total(items)))
    await db.commit()
    await db.refresh(rubric)
    return _to_response(rubric)


@router.delete("/{rubric_id}", status_code=204)
async def delete_rubric(
    rubric_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rubric = await _get_rubric_or_404(rubric_id, current_user.tenant_id, db)
    await db.delete(rubric)
    await db.commit()


# ── Coverage scoring ───────────────────────────────────────────────────────────

@router.post("/{rubric_id}/coverage/{rehearsal_id}", response_model=RubricScoreResponse, status_code=201)
async def score_coverage(
    rubric_id: int,
    rehearsal_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger LLM-based coverage scoring of a rehearsal against a rubric.
    Idempotent: if score already exists, returns existing score.
    """
    rubric = await _get_rubric_or_404(rubric_id, current_user.tenant_id, db)

    # Check rehearsal belongs to tenant
    r_res = await db.execute(
        select(Rehearsal).where(
            Rehearsal.id == rehearsal_id,
            Rehearsal.tenant_id == current_user.tenant_id,
        )
    )
    rehearsal = r_res.scalar_one_or_none()
    if not rehearsal:
        raise HTTPException(status_code=404, detail="Rehearsal not found")

    if rehearsal.status < 3:
        raise HTTPException(status_code=422, detail="Rehearsal scoring not complete yet")

    # Return cached if exists
    existing = await db.execute(
        select(RubricScore).where(
            RubricScore.rubric_id == rubric_id,
            RubricScore.rehearsal_id == rehearsal_id,
        )
    )
    rs = existing.scalar_one_or_none()
    if rs:
        return _rs_to_response(rs)

    # Build transcript from rehearsal
    transcript = _build_transcript(rehearsal)

    # Compute synchronously (fast path)
    result = await score_rehearsal_against_rubric(
        rubric_items=rubric.items,
        transcript=transcript,
    )

    rs = RubricScore(
        tenant_id=current_user.tenant_id,
        rubric_id=rubric_id,
        rehearsal_id=rehearsal_id,
        scores=result["scores"],
        total_score=Decimal(str(result["total_score"])),
        coverage_percent=Decimal(str(result["coverage_percent"])),
        coverage_detail=result["coverage_detail"],
        improvement_suggestions=result["improvement_suggestions"],
    )
    db.add(rs)
    await db.commit()
    await db.refresh(rs)
    return _rs_to_response(rs)


@router.get("/{rubric_id}/coverage/{rehearsal_id}", response_model=RubricScoreResponse)
async def get_coverage(
    rubric_id: int,
    rehearsal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(RubricScore).where(
            RubricScore.rubric_id == rubric_id,
            RubricScore.rehearsal_id == rehearsal_id,
        )
    )
    rs = existing.scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=404, detail="No rubric score found")
    return _rs_to_response(rs)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_rubric_or_404(rubric_id: int, tenant_id: int, db: AsyncSession) -> ScoringRubric:
    result = await db.execute(
        select(ScoringRubric).where(
            ScoringRubric.id == rubric_id,
            ScoringRubric.tenant_id == tenant_id,
        )
    )
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    return rubric


def _build_transcript(rehearsal: Rehearsal) -> str:
    """Build a plain text transcript from rehearsal transcript_json."""
    if not rehearsal.transcript_json:
        return ""
    parts = []
    for seg in rehearsal.transcript_json:
        if isinstance(seg, dict):
            text = seg.get("text") or seg.get("content") or ""
            if text:
                parts.append(text)
    return " ".join(parts)


def _to_response(rubric: ScoringRubric) -> RubricResponse:
    return RubricResponse(
        id=rubric.id,
        name=rubric.name,
        description=rubric.description,
        source_type=rubric.source_type,
        items=rubric.items or [],
        total_max_score=float(rubric.total_max_score) if rubric.total_max_score else None,
        industry=rubric.industry,
        template_type=rubric.template_type,
        is_template=rubric.is_template,
        created_at=rubric.created_at,
    )


def _rs_to_response(rs: RubricScore) -> RubricScoreResponse:
    return RubricScoreResponse(
        id=rs.id,
        rubric_id=rs.rubric_id,
        rehearsal_id=rs.rehearsal_id,
        scores=rs.scores or [],
        total_score=float(rs.total_score) if rs.total_score else None,
        coverage_percent=float(rs.coverage_percent) if rs.coverage_percent else None,
        coverage_detail=rs.coverage_detail,
        improvement_suggestions=rs.improvement_suggestions,
        created_at=rs.created_at,
    )
