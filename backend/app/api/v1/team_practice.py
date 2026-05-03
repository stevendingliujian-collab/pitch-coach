"""
多人组队排练 API

F_TeamPractice: 多人接力排练 — 团队中每人承担述标的一个环节，合并为完整一场。

Endpoints:
  POST /team-practice/sessions         创建会话
  GET  /team-practice/sessions         列出当前租户所有会话
  GET  /team-practice/sessions/{id}    获取会话详情+参与者列表
  POST /team-practice/sessions/{id}/join   加入会话（认领角色）
  POST /team-practice/sessions/{id}/submit 提交排练（关联 rehearsal_id）
  POST /team-practice/sessions/{id}/complete 标记会话完成（创建者）
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import PcUser
from app.models.pitch_task import PitchTask
from app.models.rehearsal import Rehearsal
from app.models.team_practice import TeamPracticeSession, TeamPracticeParticipant

router = APIRouter(prefix="/team-practice", tags=["team-practice"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RoleInput(BaseModel):
    role: str                    # e.g. "开场与公司介绍"
    description: str             # What to cover in this role
    suggested_duration_sec: int = 120

class CreateSessionRequest(BaseModel):
    pitch_task_id: int
    title: str
    description: str | None = None
    roles: list[RoleInput]       # 2-6 roles


class JoinRequest(BaseModel):
    role_index: int


class SubmitTurnRequest(BaseModel):
    rehearsal_id: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _session_to_dict(s: TeamPracticeSession) -> dict[str, Any]:
    return {
        "id": s.id,
        "pitch_task_id": s.pitch_task_id,
        "created_by": s.created_by,
        "title": s.title,
        "description": s.description,
        "roles": s.roles or [],
        "status": s.status,
        "avg_score": s.avg_score,
        "total_score": s.total_score,
        "feedback": s.feedback,
        "created_at": s.created_at.isoformat(),
    }


def _participant_to_dict(p: TeamPracticeParticipant) -> dict[str, Any]:
    return {
        "id": p.id,
        "session_id": p.session_id,
        "user_id": p.user_id,
        "role_index": p.role_index,
        "role_name": p.role_name,
        "rehearsal_id": p.rehearsal_id,
        "status": p.status,
        "score": p.score,
        "feedback": p.feedback,
        "joined_at": p.joined_at.isoformat(),
        "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/sessions", status_code=201)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
) -> dict[str, Any]:
    """创建多人组队排练会话（组长操作）"""
    if not (2 <= len(body.roles) <= 6):
        raise HTTPException(422, "角色数量必须在 2-6 之间")

    # Verify task belongs to tenant
    task = await db.get(PitchTask, body.pitch_task_id)
    if not task or task.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "述标任务不存在")

    roles_json = [r.model_dump() for r in body.roles]
    session = TeamPracticeSession(
        tenant_id=current_user.tenant_id,
        pitch_task_id=body.pitch_task_id,
        created_by=current_user.id,
        title=body.title,
        description=body.description,
        roles=roles_json,
        status=1,  # open immediately
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_to_dict(session)


@router.get("/sessions")
async def list_sessions(
    pitch_task_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """列出当前租户所有多人排练会话"""
    q = select(TeamPracticeSession).where(
        TeamPracticeSession.tenant_id == current_user.tenant_id
    )
    if pitch_task_id:
        q = q.where(TeamPracticeSession.pitch_task_id == pitch_task_id)
    q = q.order_by(TeamPracticeSession.created_at.desc()).limit(50)
    result = await db.execute(q)
    sessions = result.scalars().all()
    return [_session_to_dict(s) for s in sessions]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
) -> dict[str, Any]:
    """获取会话详情及参与者列表"""
    session = await db.get(TeamPracticeSession, session_id)
    if not session or session.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "会话不存在")

    p_res = await db.execute(
        select(TeamPracticeParticipant).where(
            TeamPracticeParticipant.session_id == session_id
        ).order_by(TeamPracticeParticipant.role_index)
    )
    participants = p_res.scalars().all()

    data = _session_to_dict(session)
    data["participants"] = [_participant_to_dict(p) for p in participants]
    return data


@router.post("/sessions/{session_id}/join", status_code=201)
async def join_session(
    session_id: int,
    body: JoinRequest,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
) -> dict[str, Any]:
    """加入会话并认领角色"""
    session = await db.get(TeamPracticeSession, session_id)
    if not session or session.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "会话不存在")
    if session.status != 1:
        raise HTTPException(400, "会话不在开放状态，无法加入")

    roles = session.roles or []
    if body.role_index < 0 or body.role_index >= len(roles):
        raise HTTPException(422, "角色索引超出范围")

    # Check role not already taken
    taken = await db.execute(
        select(TeamPracticeParticipant).where(
            TeamPracticeParticipant.session_id == session_id,
            TeamPracticeParticipant.role_index == body.role_index,
        )
    )
    if taken.scalar_one_or_none():
        raise HTTPException(409, "该角色已被其他人认领")

    # Check user hasn't already joined
    existing = await db.execute(
        select(TeamPracticeParticipant).where(
            TeamPracticeParticipant.session_id == session_id,
            TeamPracticeParticipant.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "您已加入该会话")

    role_name = roles[body.role_index].get("role", f"角色{body.role_index + 1}")
    participant = TeamPracticeParticipant(
        session_id=session_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        role_index=body.role_index,
        role_name=role_name,
        status=0,
    )
    db.add(participant)
    await db.commit()
    await db.refresh(participant)
    return _participant_to_dict(participant)


@router.post("/sessions/{session_id}/submit")
async def submit_turn(
    session_id: int,
    body: SubmitTurnRequest,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
) -> dict[str, Any]:
    """提交本轮排练（关联一个已完成的 rehearsal）"""
    session = await db.get(TeamPracticeSession, session_id)
    if not session or session.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "会话不存在")
    if session.status not in (1, 2):
        raise HTTPException(400, "会话不在可提交状态")

    # Find participant
    p_res = await db.execute(
        select(TeamPracticeParticipant).where(
            TeamPracticeParticipant.session_id == session_id,
            TeamPracticeParticipant.user_id == current_user.id,
        )
    )
    participant = p_res.scalar_one_or_none()
    if not participant:
        raise HTTPException(400, "请先加入会话再提交")

    # Verify rehearsal belongs to user
    rehearsal = await db.get(Rehearsal, body.rehearsal_id)
    if not rehearsal or rehearsal.user_id != current_user.id:
        raise HTTPException(404, "排练记录不存在")

    participant.rehearsal_id = rehearsal.id
    participant.status = 1
    participant.submitted_at = datetime.utcnow()
    if rehearsal.total_score:
        participant.score = float(rehearsal.total_score)

    # Move session to in_progress if not already
    if session.status == 1:
        session.status = 2

    await db.commit()

    # Auto-complete if all participants submitted
    p_all = await db.execute(
        select(TeamPracticeParticipant).where(
            TeamPracticeParticipant.session_id == session_id
        )
    )
    all_p = p_all.scalars().all()
    if all_p and all(p.status == 1 for p in all_p):
        scores = [p.score for p in all_p if p.score is not None]
        session.avg_score = round(sum(scores) / len(scores), 1) if scores else None
        session.total_score = session.avg_score
        session.status = 3  # completed
        await db.commit()

    await db.refresh(participant)
    return _participant_to_dict(participant)


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
) -> dict[str, Any]:
    """强制标记会话为完成（创建者/经理可以操作）"""
    session = await db.get(TeamPracticeSession, session_id)
    if not session or session.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "会话不存在")
    if session.created_by != current_user.id and current_user.role not in ("manager", "admin"):
        raise HTTPException(403, "只有创建者或管理员可以标记完成")
    if session.status == 3:
        raise HTTPException(400, "会话已完成")

    p_all = await db.execute(
        select(TeamPracticeParticipant).where(
            TeamPracticeParticipant.session_id == session_id,
            TeamPracticeParticipant.status == 1,
        )
    )
    submitted = p_all.scalars().all()
    scores = [p.score for p in submitted if p.score is not None]
    session.avg_score = round(sum(scores) / len(scores), 1) if scores else None
    session.total_score = session.avg_score
    session.status = 3
    await db.commit()
    await db.refresh(session)

    data = _session_to_dict(session)
    # re-fetch participants
    p_res = await db.execute(
        select(TeamPracticeParticipant).where(
            TeamPracticeParticipant.session_id == session_id
        ).order_by(TeamPracticeParticipant.role_index)
    )
    data["participants"] = [_participant_to_dict(p) for p in p_res.scalars().all()]
    return data
