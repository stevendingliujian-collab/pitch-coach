from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Any
from decimal import Decimal
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.evaluator import EvaluatorPersona, QASession
from app.models.pitch_task import PitchTask
from app.models.pitch_plan import PitchPlan, PlanPage
from app.services.evaluator_service import (
    get_preset_personas,
    generate_opening_questions,
    generate_followup_question,
    score_qa_session,
)

router = APIRouter(prefix="/evaluators", tags=["evaluators"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    evaluator_id: int | None = None
    # Use preset persona id (e.g. 'tech', 'business') if no DB evaluator
    preset_persona_id: str | None = None
    session_type: str = "single"


class AnswerMessage(BaseModel):
    answer: str
    question_index: int | None = None


class PersonaResponse(BaseModel):
    id: Any  # int (DB) or str (preset)
    name: str
    role: str
    description: str | None
    avatar_emoji: str | None
    difficulty: int
    focus_areas: list[str] | None
    persona_type: str


class SessionResponse(BaseModel):
    id: int
    evaluator_id: int | None
    preset_persona_id: str | None
    session_type: str
    messages: list[Any]
    status: int
    total_score: float | None
    feedback: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Preset personas ────────────────────────────────────────────────────────────

@router.get("/presets", response_model=list[PersonaResponse])
async def list_presets():
    """Return built-in evaluator personas (no auth needed)."""
    return [
        PersonaResponse(
            id=p["id"],
            name=p["name"],
            role=p["role"],
            description=p.get("description"),
            avatar_emoji=p.get("avatar_emoji"),
            difficulty=p.get("difficulty", 3),
            focus_areas=p.get("focus_areas"),
            persona_type="system",
        )
        for p in get_preset_personas()
    ]


# ── Custom personas CRUD ───────────────────────────────────────────────────────

@router.get("", response_model=list[PersonaResponse])
async def list_evaluators(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EvaluatorPersona)
        .where(
            EvaluatorPersona.tenant_id == current_user.tenant_id,
            EvaluatorPersona.is_active == True,
        )
        .order_by(EvaluatorPersona.created_at.desc())
    )
    evaluators = result.scalars().all()
    return [_persona_to_response(e) for e in evaluators]


# ── QA Sessions ────────────────────────────────────────────────────────────────

@router.post("/sessions/{task_id}", response_model=SessionResponse, status_code=201)
async def start_session(
    task_id: int,
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new QA simulation session. Generates opening questions automatically."""
    # Verify task
    task = await _get_task_or_404(task_id, current_user.tenant_id, db)

    # Resolve persona
    persona = await _resolve_persona(body, current_user.tenant_id, db)
    if not persona:
        raise HTTPException(status_code=404, detail="Evaluator persona not found")

    # Build pitch context from latest plan
    pitch_content = await _build_pitch_context(task_id, current_user.tenant_id, db)

    # Generate opening questions
    num_q = 3 + (persona.get("difficulty", 3) - 1)  # 3-7 questions based on difficulty
    num_q = min(max(num_q, 2), 5)
    questions = await generate_opening_questions(persona, pitch_content, num_questions=num_q)

    # Seed messages with opening questions
    messages = []
    for q in questions:
        messages.append({"role": "evaluator", "content": q, "answered": False})

    # Create session
    session = QASession(
        tenant_id=current_user.tenant_id,
        pitch_task_id=task_id,
        user_id=current_user.id,
        evaluator_id=body.evaluator_id,
        session_type=body.session_type,
        messages=messages,
        status=1,  # in_progress
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_to_response(session, body.preset_persona_id)


@router.post("/sessions/{session_id}/answer", response_model=SessionResponse)
async def submit_answer(
    session_id: int,
    body: AnswerMessage,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit an answer to the current question. May generate a follow-up."""
    session = await _get_session_or_404(session_id, current_user.tenant_id, db)
    if session.status == 2:
        raise HTTPException(status_code=422, detail="Session already completed")

    messages = list(session.messages or [])

    # Find the last unanswered evaluator question
    last_q_idx = None
    for i, msg in enumerate(messages):
        if msg["role"] == "evaluator" and not msg.get("answered"):
            last_q_idx = i
            break

    if last_q_idx is None:
        raise HTTPException(status_code=422, detail="No pending question to answer")

    # Mark question as answered
    messages[last_q_idx]["answered"] = True

    # Append user answer
    messages.append({"role": "user", "content": body.answer})

    # Get persona for follow-up logic
    persona = await _resolve_persona_from_session(session, db)

    # Check if there are more unanswered questions
    has_more = any(
        m["role"] == "evaluator" and not m.get("answered")
        for m in messages
    )

    if not has_more and persona:
        # Possibly generate a follow-up for the last answer
        followup = await generate_followup_question(
            persona,
            question=messages[last_q_idx]["content"],
            answer=body.answer,
        )
        if followup:
            messages.append({"role": "evaluator", "content": followup, "answered": False})
            has_more = True

    session.messages = messages

    # If no more questions, complete session
    if not has_more:
        session.status = 2  # completed
        if persona:
            score_result = await score_qa_session(persona, messages)
            session.total_score = Decimal(str(score_result.get("total_score", 0)))
            session.feedback = score_result.get("feedback", "")

    await db.commit()
    await db.refresh(session)
    return _session_to_response(session)


@router.post("/sessions/{session_id}/complete", response_model=SessionResponse)
async def complete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Force-complete session and generate final score."""
    session = await _get_session_or_404(session_id, current_user.tenant_id, db)
    if session.status == 2:
        return _session_to_response(session)

    persona = await _resolve_persona_from_session(session, db)
    session.status = 2
    if persona:
        score_result = await score_qa_session(persona, session.messages or [])
        session.total_score = Decimal(str(score_result.get("total_score", 0)))
        session.feedback = score_result.get("feedback", "")

    await db.commit()
    await db.refresh(session)
    return _session_to_response(session)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    task_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(QASession).where(
        QASession.tenant_id == current_user.tenant_id,
        QASession.user_id == current_user.id,
    )
    if task_id:
        q = q.where(QASession.pitch_task_id == task_id)
    q = q.order_by(QASession.created_at.desc())
    result = await db.execute(q)
    sessions = result.scalars().all()
    return [_session_to_response(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(session_id, current_user.tenant_id, db)
    return _session_to_response(session)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_task_or_404(task_id: int, tenant_id: int, db: AsyncSession) -> PitchTask:
    result = await db.execute(
        select(PitchTask).where(PitchTask.id == task_id, PitchTask.tenant_id == tenant_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def _get_session_or_404(session_id: int, tenant_id: int, db: AsyncSession) -> QASession:
    result = await db.execute(
        select(QASession).where(
            QASession.id == session_id,
            QASession.tenant_id == tenant_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _resolve_persona(
    body: SessionCreate, tenant_id: int, db: AsyncSession
) -> dict | None:
    """Resolve to a persona dict (preset or DB)."""
    if body.preset_persona_id:
        presets = {p["id"]: p for p in get_preset_personas()}
        return presets.get(body.preset_persona_id)
    if body.evaluator_id:
        result = await db.execute(
            select(EvaluatorPersona).where(
                EvaluatorPersona.id == body.evaluator_id,
                EvaluatorPersona.tenant_id == tenant_id,
            )
        )
        ep = result.scalar_one_or_none()
        if ep:
            return {
                "id": ep.id,
                "name": ep.name,
                "role": ep.role,
                "system_prompt": ep.system_prompt,
                "difficulty": ep.difficulty,
                "focus_areas": ep.focus_areas or [],
            }
    return None


async def _resolve_persona_from_session(
    session: QASession, db: AsyncSession
) -> dict | None:
    """Try to get persona from session's evaluator_id (DB persona)."""
    if session.evaluator_id:
        result = await db.execute(
            select(EvaluatorPersona).where(EvaluatorPersona.id == session.evaluator_id)
        )
        ep = result.scalar_one_or_none()
        if ep:
            return {
                "id": ep.id,
                "name": ep.name,
                "role": ep.role,
                "system_prompt": ep.system_prompt,
                "difficulty": ep.difficulty,
            }
    # Fallback: default tech persona
    presets = {p["id"]: p for p in get_preset_personas()}
    return presets.get("tech")


async def _build_pitch_context(task_id: int, tenant_id: int, db: AsyncSession) -> str:
    """Build a text summary of the pitch plan for context."""
    plans_res = await db.execute(
        select(PitchPlan).where(
            PitchPlan.pitch_task_id == task_id,
            PitchPlan.tenant_id == tenant_id,
        ).order_by(PitchPlan.created_at.desc())
    )
    plan = plans_res.scalars().first()
    if not plan:
        return ""

    pages_res = await db.execute(
        select(PlanPage).where(PlanPage.plan_id == plan.id).order_by(PlanPage.page_number)
    )
    pages = pages_res.scalars().all()

    parts = []
    for page in pages[:15]:  # cap at 15 pages
        title = page.title or ""
        content = (page.content or "")[:200]
        parts.append(f"第{page.page_number}页 {title}: {content}")
    return "\n".join(parts)


def _persona_to_response(ep: EvaluatorPersona) -> PersonaResponse:
    return PersonaResponse(
        id=ep.id,
        name=ep.name,
        role=ep.role,
        description=ep.description,
        avatar_emoji=ep.avatar_emoji,
        difficulty=ep.difficulty,
        focus_areas=ep.focus_areas,
        persona_type=ep.persona_type,
    )


def _session_to_response(session: QASession, preset_persona_id: str | None = None) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        evaluator_id=session.evaluator_id,
        preset_persona_id=preset_persona_id,
        session_type=session.session_type,
        messages=session.messages or [],
        status=session.status,
        total_score=float(session.total_score) if session.total_score else None,
        feedback=session.feedback,
        created_at=session.created_at,
    )
