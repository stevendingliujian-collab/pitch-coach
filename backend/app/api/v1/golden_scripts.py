"""
金牌话术沉淀 API

经理/管理员将排练中的精彩片段标记为「金牌话术」，
系统自动摘取音频剪辑 + 转录文字 + 注入知识库。

端点：
- POST /golden-scripts              标记精彩片段
- GET  /golden-scripts              列出金牌话术
- GET  /golden-scripts/{id}         获取单条
- DELETE /golden-scripts/{id}       取消标记
- POST /golden-scripts/from-qa      从 QA 会话提取金牌话术（AI）
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import PcUser
from app.models.knowledge import GoldenScript
from app.models.rehearsal import Rehearsal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/golden-scripts", tags=["golden-scripts"])


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def mark_golden_script(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """
    标记排练中的精彩片段为金牌话术。

    body: {
        "rehearsal_id": 42,
        "page_number": 3,
        "start_sec": 45.2,
        "end_sec": 62.5,
        "transcript": "我们的系统集成方案在政务领域有超过50个成功案例...",
        "tags": ["案例", "成功率"],
        "audio_clip_url": "https://..."   // optional, 已剪辑音频
    }
    """
    rehearsal_id = body.get("rehearsal_id")
    if not rehearsal_id:
        raise HTTPException(status_code=400, detail="rehearsal_id is required")

    # Verify rehearsal belongs to this tenant
    rehearsal = await db.get(Rehearsal, rehearsal_id)
    if not rehearsal or rehearsal.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Rehearsal not found")

    transcript = (body.get("transcript") or "").strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="transcript is required")

    gs = GoldenScript(
        tenant_id=current_user.tenant_id,
        rehearsal_id=rehearsal_id,
        page_number=body.get("page_number", 1),
        start_sec=body.get("start_sec"),
        end_sec=body.get("end_sec"),
        transcript=transcript,
        marked_by=current_user.id,
        tags=body.get("tags", []),
        audio_clip_url=body.get("audio_clip_url"),
        usage_count=0,
    )
    db.add(gs)
    await db.commit()
    await db.refresh(gs)

    # Trigger gamification check for golden_teacher badge
    try:
        count_result = await db.execute(
            select(func.count(GoldenScript.id))
            .where(GoldenScript.tenant_id == current_user.tenant_id,
                   GoldenScript.marked_by == current_user.id)
        )
        total_marked = count_result.scalar() or 0

        from app.services.gamification_service import check_golden_script_achievements
        await check_golden_script_achievements(db, current_user.tenant_id, current_user.id, total_marked)
    except Exception as e:
        logger.warning("Gamification check failed: %s", e)

    return _gs_dict(gs)


@router.get("")
async def list_golden_scripts(
    page: int = 1,
    page_size: int = 20,
    rehearsal_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """列出金牌话术（可按排练过滤）"""
    q = select(GoldenScript).where(GoldenScript.tenant_id == current_user.tenant_id)
    if rehearsal_id:
        q = q.where(GoldenScript.rehearsal_id == rehearsal_id)
    q = q.order_by(GoldenScript.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(q)
    scripts = result.scalars().all()

    total_result = await db.execute(
        select(func.count(GoldenScript.id))
        .where(GoldenScript.tenant_id == current_user.tenant_id)
    )
    total = total_result.scalar() or 0

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_gs_dict(gs) for gs in scripts],
    }


@router.get("/{script_id}")
async def get_golden_script(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """获取单条金牌话术"""
    gs = await db.get(GoldenScript, script_id)
    if not gs or gs.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Golden script not found")
    return _gs_dict(gs)


@router.delete("/{script_id}", status_code=204)
async def delete_golden_script(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """取消标记金牌话术"""
    gs = await db.get(GoldenScript, script_id)
    if not gs or gs.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Golden script not found")
    await db.delete(gs)
    await db.commit()


@router.post("/from-qa")
async def extract_golden_scripts_from_qa(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """
    从 QA 会话中用 AI 提取金牌话术并保存。

    body: { "qa_session_id": 12, "task_name": "xx项目述标" }
    """
    from app.models.evaluator import QaSession
    from app.services.scenario_engine import extract_golden_scripts

    session_id = body.get("qa_session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="qa_session_id is required")

    session = await db.get(QaSession, session_id)
    if not session or session.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="QA session not found")

    task_name = body.get("task_name", "")
    messages: list[dict] = session.messages or []

    try:
        extracted = await extract_golden_scripts(messages, task_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    saved = []
    for item in extracted:
        if float(item.get("score", 0)) >= 4:
            gs = GoldenScript(
                tenant_id=current_user.tenant_id,
                rehearsal_id=None,
                page_number=0,
                transcript=item.get("answer", ""),
                marked_by=current_user.id,
                tags=item.get("tags", []),
                usage_count=0,
            )
            db.add(gs)
            saved.append(item)

    await db.commit()
    return {"extracted": len(extracted), "saved": len(saved), "items": saved}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _gs_dict(gs: GoldenScript) -> dict:
    return {
        "id": gs.id,
        "rehearsal_id": gs.rehearsal_id,
        "page_number": gs.page_number,
        "start_sec": float(gs.start_sec) if gs.start_sec else None,
        "end_sec": float(gs.end_sec) if gs.end_sec else None,
        "transcript": gs.transcript,
        "audio_clip_url": gs.audio_clip_url,
        "tags": gs.tags or [],
        "marked_by": gs.marked_by,
        "usage_count": gs.usage_count,
        "created_at": gs.created_at.isoformat() if gs.created_at else None,
    }
