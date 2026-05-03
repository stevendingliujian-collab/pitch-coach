"""
F7 AI 复盘助手 API

端点：
- POST /post-mortem/{task_id}          创建复盘，上传录音，触发异步分析
- GET  /post-mortem/{task_id}          获取该任务所有复盘列表
- GET  /post-mortem/reports/{id}       获取单个复盘报告（含完整分析结果）
- DELETE /post-mortem/reports/{id}     删除复盘报告
- GET  /post-mortem/reports/{id}/followup  获取答疑函草稿（纯文本）
"""
from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import PcUser
from app.models.post_mortem import PostMortem
from app.models.pitch_task import PitchTask
from app.core.storage import upload_bytes

router = APIRouter(prefix="/post-mortem", tags=["post-mortem"])


# ─── 创建复盘（上传录音） ──────────────────────────────────────────────────────

@router.post("/{task_id}", status_code=201)
async def create_post_mortem(
    task_id: int,
    file: UploadFile = File(..., description="述标会议录音（mp3/wav/m4a，建议<200MB）"),
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """上传述标会议录音，创建复盘报告并启动 AI 分析任务"""
    # Verify task belongs to tenant
    task = await db.get(PitchTask, task_id)
    if not task or task.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Task not found")

    # Upload recording to storage
    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    ext = (file.filename or "recording.mp3").rsplit(".", 1)[-1].lower()
    storage_key = (
        f"{current_user.tenant_id}/pitch-coach/post-mortems/"
        f"{task_id}/{uuid.uuid4().hex}.{ext}"
    )
    upload_bytes(storage_key, audio_bytes, file.content_type or "audio/mpeg")

    # Create DB record
    pm = PostMortem(
        tenant_id=current_user.tenant_id,
        pitch_task_id=task_id,
        user_id=current_user.id,
        recording_url=storage_key,
        recording_duration=None,
        status="pending",
    )
    db.add(pm)
    await db.flush()

    # Dispatch Celery task
    from app.workers.tasks import run_post_mortem_task
    celery_task = run_post_mortem_task.delay(pm.id)
    pm.task_id = celery_task.id
    await db.commit()
    await db.refresh(pm)

    return {
        "id": pm.id,
        "status": pm.status,
        "task_id": pm.task_id,
        "pitch_task_id": pm.pitch_task_id,
        "created_at": pm.created_at.isoformat(),
        "message": "复盘分析已启动，通常需要2-5分钟，请稍后查看结果"
    }


# ─── 获取任务下所有复盘 ────────────────────────────────────────────────────────

@router.get("/{task_id}")
async def list_post_mortems(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """获取述标任务下所有复盘报告列表"""
    result = await db.execute(
        select(PostMortem)
        .where(
            PostMortem.tenant_id == current_user.tenant_id,
            PostMortem.pitch_task_id == task_id,
        )
        .order_by(PostMortem.created_at.desc())
    )
    reports = result.scalars().all()
    return [_summary(pm) for pm in reports]


# ─── 获取单个复盘详情 ─────────────────────────────────────────────────────────

@router.get("/reports/{pm_id}")
async def get_post_mortem(
    pm_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """获取复盘报告完整内容"""
    pm = await db.get(PostMortem, pm_id)
    if not pm or pm.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Post-mortem report not found")

    return _full_report(pm)


# ─── 删除复盘 ─────────────────────────────────────────────────────────────────

@router.delete("/reports/{pm_id}", status_code=204)
async def delete_post_mortem(
    pm_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    pm = await db.get(PostMortem, pm_id)
    if not pm or pm.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(pm)
    await db.commit()


# ─── 获取答疑函草稿 ───────────────────────────────────────────────────────────

@router.get("/reports/{pm_id}/followup")
async def get_followup_draft(
    pm_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """获取答疑跟进函草稿（Markdown 格式）"""
    pm = await db.get(PostMortem, pm_id)
    if not pm or pm.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Not found")
    if pm.status != "completed":
        raise HTTPException(status_code=202, detail="Analysis not yet complete")
    return {
        "id": pm.id,
        "followup_draft": pm.followup_draft or "",
        "pitch_task_id": pm.pitch_task_id,
    }


# ─── 重新触发分析（失败时重试） ───────────────────────────────────────────────

@router.post("/reports/{pm_id}/retry", status_code=202)
async def retry_post_mortem(
    pm_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """重新触发失败的复盘分析任务"""
    pm = await db.get(PostMortem, pm_id)
    if not pm or pm.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Not found")
    if pm.status not in ("failed", "pending"):
        raise HTTPException(status_code=400, detail="Only failed or pending reports can be retried")

    pm.status = "pending"
    pm.error_msg = None
    await db.flush()

    from app.workers.tasks import run_post_mortem_task
    celery_task = run_post_mortem_task.delay(pm.id)
    pm.task_id = celery_task.id
    await db.commit()
    return {"id": pm.id, "status": "pending", "task_id": pm.task_id}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _summary(pm: PostMortem) -> dict:
    return {
        "id": pm.id,
        "pitch_task_id": pm.pitch_task_id,
        "status": pm.status,
        "question_count": pm.question_count,
        "our_talk_ratio": float(pm.our_talk_ratio) if pm.our_talk_ratio is not None else None,
        "prediction_hit_rate": float(pm.prediction_hit_rate) if pm.prediction_hit_rate is not None else None,
        "overall_score": (pm.insights or {}).get("overall_score") if pm.insights else None,
        "grade": (pm.insights or {}).get("grade") if pm.insights else None,
        "created_at": pm.created_at.isoformat(),
        "updated_at": pm.updated_at.isoformat(),
        "error_msg": pm.error_msg,
    }


def _full_report(pm: PostMortem) -> dict:
    base = _summary(pm)
    base.update({
        "evaluator_count": pm.evaluator_count,
        "question_categories": pm.question_categories,
        "evaluator_questions": pm.evaluator_questions or [],
        "answer_assessments": pm.answer_assessments or [],
        "key_moments": pm.key_moments or [],
        "insights": pm.insights or {},
        "followup_draft": pm.followup_draft,
        # Omit raw diarization for brevity (can be separate endpoint if needed)
        "diarization_segment_count": len(pm.diarization or []),
    })
    return base
