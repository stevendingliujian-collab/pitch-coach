"""
F8 动态场景引擎 API

端点：
- GET  /scenarios                  获取所有预建场景（可按 industry/difficulty 过滤）
- GET  /scenarios/{id}             获取单个场景详情
- POST /scenarios/{id}/start       基于场景启动 QA 会话（集成到评委模拟）
- GET  /scenarios/industries       获取所有行业分类
- POST /scenarios/adaptive-difficulty  计算自适应难度
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import PcUser
from app.models.evaluator import QaSession
from app.services.scenario_engine import (
    PRESET_SCENARIOS,
    get_scenario,
    list_scenarios,
    calculate_adaptive_difficulty,
    get_difficulty_label,
    generate_scenario_questions,
)
from app.services.evaluator_service import PRESET_PERSONAS

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

INDUSTRIES = {
    "system_integration": "系统集成",
    "software_dev": "软件开发",
    "automation": "非标自动化",
    "general": "通用能力",
}


# ─── 获取场景列表 ─────────────────────────────────────────────────────────────

@router.get("")
async def list_all_scenarios(
    industry: str | None = Query(None, description="行业分类过滤"),
    difficulty: int | None = Query(None, ge=1, le=5, description="难度等级过滤"),
    search: str | None = Query(None, description="关键词搜索"),
    current_user: PcUser = Depends(get_current_user),
):
    """获取所有预建场景，可按行业和难度过滤"""
    scenarios = list_scenarios(industry=industry, difficulty=difficulty)

    if search:
        search_lower = search.lower()
        scenarios = [
            s for s in scenarios
            if search_lower in s["name"].lower()
            or search_lower in s["description"].lower()
            or any(search_lower in t.lower() for t in s.get("tags", []))
        ]

    return [_scenario_summary(s) for s in scenarios]


# ─── 获取行业列表 ─────────────────────────────────────────────────────────────

@router.get("/industries")
async def get_industries(current_user: PcUser = Depends(get_current_user)):
    """获取所有行业分类及场景数量"""
    result = []
    for industry_id, industry_name in INDUSTRIES.items():
        count = len([s for s in PRESET_SCENARIOS if s["industry"] == industry_id])
        result.append({
            "id": industry_id,
            "name": industry_name,
            "scenario_count": count,
        })
    return result


# ─── 获取单个场景 ─────────────────────────────────────────────────────────────

@router.get("/{scenario_id}")
async def get_scenario_detail(
    scenario_id: str,
    current_user: PcUser = Depends(get_current_user),
):
    """获取场景完整详情"""
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return _scenario_full(scenario)


# ─── 基于场景启动 QA 会话 ─────────────────────────────────────────────────────

@router.post("/{scenario_id}/start", status_code=201)
async def start_scenario_session(
    scenario_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """
    基于指定场景和评委画像创建 QA 会话，自动生成场景专属问题。

    body: {
        "task_id": int,                  // 关联的述标任务
        "persona_id": "tech" | "business" | ...,
        "difficulty": 1-5 (optional),   // 覆盖默认难度
        "pitch_summary": "方案摘要"     // 可选，不提供则用空
    }
    """
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    task_id = body.get("task_id")
    persona_id = body.get("persona_id", scenario["evaluator_types"][0])
    difficulty = body.get("difficulty", scenario["difficulty"])
    pitch_summary = body.get("pitch_summary", "")

    # Find persona
    persona = next((p for p in PRESET_PERSONAS if p["id"] == persona_id), None)
    if not persona:
        raise HTTPException(status_code=400, detail=f"Unknown persona '{persona_id}'")

    # Generate scenario-specific opening questions
    num_q = 3
    questions: list[str] = []
    try:
        # Build pitch content from task if available
        pitch_content = pitch_summary
        if task_id and not pitch_content:
            from sqlalchemy import select as sa_select
            from app.models.pitch_plan import PitchPlan
            plan_res = await db.execute(
                sa_select(PitchPlan)
                .where(
                    PitchPlan.pitch_task_id == task_id,
                    PitchPlan.tenant_id == current_user.tenant_id,
                    PitchPlan.status == 1,
                )
                .order_by(PitchPlan.id.desc())
                .limit(1)
            )
            plan = plan_res.scalar_one_or_none()
            if plan:
                pitch_content = f"{plan.ppt_file_name}\n" + "\n".join(
                    p.get("talking_points", [])[:2]
                    for p in (plan.predicted_questions or [])[:3]
                    if isinstance(p, dict)
                )

        questions = await generate_scenario_questions(
            scenario=scenario,
            persona=persona,
            pitch_content=pitch_content or scenario["background"],
            difficulty=difficulty,
            num_questions=num_q,
        )
    except Exception:
        # Fall back to preset common questions
        questions = scenario["common_questions"][:num_q]

    # Create QA session
    messages: list[dict] = []
    for i, q in enumerate(questions):
        messages.append({
            "role": "question",
            "content": q,
            "persona": persona_id,
            "question_index": i,
        })

    session = QaSession(
        tenant_id=current_user.tenant_id,
        pitch_task_id=task_id or 0,
        user_id=current_user.id,
        evaluator_id=None,
        messages=messages,
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return {
        "session_id": session.id,
        "scenario": _scenario_summary(scenario),
        "persona": _persona_summary(persona),
        "difficulty": difficulty,
        "difficulty_label": get_difficulty_label(difficulty),
        "opening_questions": questions,
        "checklist": scenario.get("checklist", []),
        "duration_min": scenario.get("duration_min", 20),
        "message": f"场景「{scenario['name']}」已就绪，共 {len(questions)} 个问题"
    }


# ─── 自适应难度计算 ───────────────────────────────────────────────────────────

@router.post("/adaptive-difficulty")
async def get_adaptive_difficulty(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """
    基于历史会话评分，计算下次推荐的场景难度。

    body: {
        "current_difficulty": 3,
        "recent_scores": [75, 82, 65]  // 最近几次 QA 会话总分
    }
    """
    current_difficulty = body.get("current_difficulty", 3)
    recent_scores = body.get("recent_scores", [])

    # Auto-fetch from DB if not provided
    if not recent_scores:
        result = await db.execute(
            select(QaSession)
            .where(
                QaSession.tenant_id == current_user.tenant_id,
                QaSession.status == "completed",
                QaSession.total_score.is_not(None),
            )
            .order_by(QaSession.id.desc())
            .limit(5)
        )
        sessions = result.scalars().all()
        recent_scores = [float(s.total_score) for s in sessions if s.total_score is not None]

    new_difficulty = calculate_adaptive_difficulty(recent_scores, current_difficulty)
    return {
        "current_difficulty": current_difficulty,
        "current_label": get_difficulty_label(current_difficulty),
        "recommended_difficulty": new_difficulty,
        "recommended_label": get_difficulty_label(new_difficulty),
        "reason": (
            "连续2次评分≥80，建议提升难度" if new_difficulty > current_difficulty
            else "连续2次评分<50，建议降低难度" if new_difficulty < current_difficulty
            else "保持当前难度"
        ),
        "recent_scores": recent_scores[-3:],
    }


# ─── Recommended scenarios for a task ────────────────────────────────────────

@router.get("/recommend/{task_id}")
async def recommend_scenarios(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """
    根据述标任务的行业和历史练习情况，推荐3-5个场景。
    """
    from app.models.pitch_task import PitchTask

    task = await db.get(PitchTask, task_id)
    if not task or task.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Task not found")

    # Map customer_industry to scenario industry
    industry_map = {
        "政府": "system_integration",
        "医疗": "system_integration",
        "金融": "software_dev",
        "教育": "software_dev",
        "制造": "automation",
        "物流": "system_integration",
        "零售": "software_dev",
        "能源": "system_integration",
        "电信": "system_integration",
    }

    industry = None
    if task.customer_industry:
        for key, val in industry_map.items():
            if key in (task.customer_industry or ""):
                industry = val
                break

    # Get relevant scenarios
    all_scenarios = list_scenarios(industry=industry) if industry else PRESET_SCENARIOS[:5]

    # Always include a general scenario
    general = [s for s in PRESET_SCENARIOS if s["industry"] == "general"][:2]
    combined = all_scenarios[:3] + general

    return {
        "task_name": task.name,
        "customer_industry": task.customer_industry,
        "recommended": [_scenario_summary(s) for s in combined[:5]],
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _scenario_summary(s: dict) -> dict:
    return {
        "id": s["id"],
        "industry": s["industry"],
        "name": s["name"],
        "customer_type": s["customer_type"],
        "difficulty": s["difficulty"],
        "difficulty_label": get_difficulty_label(s["difficulty"]),
        "duration_min": s["duration_min"],
        "description": s["description"],
        "tags": s.get("tags", []),
        "evaluator_types": s.get("evaluator_types", []),
    }


def _scenario_full(s: dict) -> dict:
    base = _scenario_summary(s)
    base.update({
        "background": s["background"],
        "key_challenges": s["key_challenges"],
        "checklist": s["checklist"],
        "common_questions": s["common_questions"],
    })
    return base


def _persona_summary(p: dict) -> dict:
    return {
        "id": p["id"],
        "name": p["name"],
        "role": p["role"],
        "description": p["description"],
        "avatar_emoji": p.get("avatar_emoji", "👤"),
        "difficulty": p["difficulty"],
        "focus_areas": p.get("focus_areas", []),
    }
