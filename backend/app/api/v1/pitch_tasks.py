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
from app.models.narration import DemoNarration
from app.models.review import Certification
from app.models.evaluator import QASession
from app.models.rubric import RubricScore

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


@router.patch("/{task_id}/outcome", response_model=PitchTaskResponse)
async def set_outcome(
    task_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """快速标记赢单/未中标结果。body: { "result": 1|2|3|4 }"""
    task = await _get_task_or_404(task_id, current_user.tenant_id, db)
    result_val = body.get("result")
    if result_val not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="result must be 1 (中标), 2 (未中标), 3 (弃标), 4 (流标)")
    task.result = result_val
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}/readiness")
async def get_readiness(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    述标 SOP 7步就绪清单：
    1. 讲解方案生成
    2. AI 示范讲解制作
    3. 排练练习 ≥ 3 次
    4. 排练最高分 ≥ 80 分
    5. 评委模拟 ≥ 1 轮
    6. 经理审核通过
    7. 评分表对标 ≥ 70%
    """
    # Verify task belongs to tenant
    task = await _get_task_or_404(task_id, current_user.tenant_id, db)

    # ── 1. Plan exists ────────────────────────────────────────────────────────
    from app.models.pitch_plan import PitchPlan
    plan_res = await db.execute(
        select(PitchPlan).where(
            PitchPlan.pitch_task_id == task_id,
            PitchPlan.tenant_id == current_user.tenant_id,
        ).order_by(PitchPlan.created_at.desc()).limit(1)
    )
    plan = plan_res.scalar_one_or_none()
    has_plan = plan is not None

    # ── 2. Demo narration ready ────────────────────────────────────────────────
    has_narration = False
    if plan:
        nar_res = await db.execute(
            select(DemoNarration).where(
                DemoNarration.plan_id == plan.id,
                DemoNarration.status == 4,  # ready
            ).limit(1)
        )
        has_narration = nar_res.scalar_one_or_none() is not None

    # ── 3 & 4. Rehearsal stats ────────────────────────────────────────────────
    reh_agg = await db.execute(
        select(
            func.count(Rehearsal.id).label("cnt"),
            func.max(Rehearsal.total_score).label("best"),
        ).where(
            Rehearsal.pitch_task_id == task_id,
            Rehearsal.tenant_id == current_user.tenant_id,
            Rehearsal.status >= 3,
        )
    )
    reh_row = reh_agg.one()
    rehearsal_count = reh_row.cnt or 0
    best_score = float(reh_row.best) if reh_row.best else 0.0

    # ── 5. QA session ─────────────────────────────────────────────────────────
    qa_res = await db.execute(
        select(QASession).where(
            QASession.pitch_task_id == task_id,
            QASession.tenant_id == current_user.tenant_id,
        ).limit(1)
    )
    has_qa = qa_res.scalar_one_or_none() is not None

    # ── 6. Certification passed ───────────────────────────────────────────────
    cert_res = await db.execute(
        select(Certification).where(
            Certification.pitch_task_id == task_id,
            Certification.tenant_id == current_user.tenant_id,
            Certification.status == 1,  # passed
        ).limit(1)
    )
    has_cert = cert_res.scalar_one_or_none() is not None

    # ── 7. Rubric coverage ≥ 70% ──────────────────────────────────────────────
    rubric_res = await db.execute(
        select(RubricScore).join(
            Rehearsal, RubricScore.rehearsal_id == Rehearsal.id
        ).where(
            Rehearsal.pitch_task_id == task_id,
            Rehearsal.tenant_id == current_user.tenant_id,
            RubricScore.coverage_percent >= 0.70,
        ).limit(1)
    )
    has_rubric = rubric_res.scalar_one_or_none() is not None

    steps = [
        {
            "key": "plan",
            "label": "讲解方案生成",
            "desc": "AI 已生成逐页讲解方案" if has_plan else "尚未生成讲解方案",
            "done": has_plan,
            "action_tab": "plan",
        },
        {
            "key": "narration",
            "label": "AI 示范讲解制作",
            "desc": "AI 示范音频已生成" if has_narration else "尚未制作 AI 示范讲解",
            "done": has_narration,
            "action_tab": "narration",
        },
        {
            "key": "rehearsal_count",
            "label": f"排练练习 ≥ 3 次（已排 {rehearsal_count} 次）",
            "desc": f"已完成 {rehearsal_count} 次有评分排练" if rehearsal_count >= 3 else f"还需 {3 - rehearsal_count} 次排练",
            "done": rehearsal_count >= 3,
            "action_tab": "rehearsal",
        },
        {
            "key": "rehearsal_score",
            "label": f"排练最高分 ≥ 80 分（当前 {best_score:.0f} 分）",
            "desc": f"最佳得分 {best_score:.0f} 分，已达标" if best_score >= 80 else "最佳得分未达到 80 分",
            "done": best_score >= 80,
            "action_tab": "rehearsal",
        },
        {
            "key": "evaluator",
            "label": "评委模拟 ≥ 1 轮",
            "desc": "已完成评委模拟问答" if has_qa else "尚未进行评委模拟",
            "done": has_qa,
            "action_tab": None,  # links to EvaluatorView
        },
        {
            "key": "certification",
            "label": "经理审核通过",
            "desc": "已获经理认证" if has_cert else "尚未提交经理审核",
            "done": has_cert,
            "action_tab": "review",
        },
        {
            "key": "rubric",
            "label": "评分表对标 ≥ 70%",
            "desc": "评分表覆盖度已达标" if has_rubric else "尚未完成评分表对标（覆盖度 ≥ 70%）",
            "done": has_rubric,
            "action_tab": "rubric",
        },
    ]

    done_count = sum(1 for s in steps if s["done"])
    progress_pct = round(done_count / len(steps) * 100)

    return {
        "task_id": task_id,
        "task_name": task.name,
        "bid_date": task.bid_date.isoformat() if task.bid_date else None,
        "done_count": done_count,
        "total_steps": len(steps),
        "progress_pct": progress_pct,
        "steps": steps,
    }


async def _get_task_or_404(task_id: int, tenant_id: int, db: AsyncSession) -> PitchTask:
    result = await db.execute(
        select(PitchTask).where(PitchTask.id == task_id, PitchTask.tenant_id == tenant_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
