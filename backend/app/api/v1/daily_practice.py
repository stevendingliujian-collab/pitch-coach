"""
F9 每日微练习 API

Key design decisions:
- Completely free, unlimited — no quota checks
- Rule-based lightweight scoring (no heavy LLM call)
- One "today" practice item per user per day; re-doing replaces the record
- Streak logic: consecutive calendar days with at least one completed practice
"""
import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import get_presigned_upload_url, get_presigned_download_url
from app.models.user import User
from app.models.daily_practice import DailyPracticeItem, DailyPracticeLog, UserStreak
from app.services.scoring_engine import detect_filler_words

router = APIRouter(prefix="/daily-practice", tags=["daily-practice"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UpcomingTask(BaseModel):
    task_id: int
    name: str
    bid_date: date
    days_left: int


class TodayPracticeResponse(BaseModel):
    item_id: int
    practice_type: str
    title: str
    instruction: str
    target_duration_sec: int
    key_points: list[str]
    log_id: Optional[int] = None
    status: int = 0   # 0=未开始/录制中 1=已完成
    # Streak info
    current_streak: int = 0
    last_practice_date: Optional[date] = None
    # Upcoming pitch within 14 days
    upcoming_task: Optional[UpcomingTask] = None


class StartPracticeResponse(BaseModel):
    log_id: int
    upload_url: str
    object_key: str


class CompletePracticeRequest(BaseModel):
    log_id: int
    object_key: str
    audio_duration_sec: int
    transcript: Optional[str] = None  # client-side transcript; None = use stub


class PracticeScoreResponse(BaseModel):
    log_id: int
    total_score: float
    completion_ok: bool
    timing_sec: int
    filler_count: int
    keyword_hit_rate: float
    feedback: list[str]
    reference_answer: Optional[str]
    # Updated streak
    current_streak: int
    longest_streak: int
    is_new_record: bool


class PracticeHistoryItem(BaseModel):
    log_id: int
    practice_date: date
    title: str
    practice_type: str
    total_score: Optional[float]
    status: int
    audio_duration_sec: Optional[int]


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    total_practices: int
    last_practice_date: Optional[date]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/today", response_model=TodayPracticeResponse)
async def get_today_practice(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return today's practice item and user's current streak.

    When a bid_date is within 14 days, switches to bid-specific warm-up content
    so the user stays focused on the upcoming pitch.
    """
    today = date.today()
    weekday = today.weekday()  # 0=Mon ... 6=Sun

    # ── Check for upcoming pitch within 14 days ──────────────────────────────
    from app.models.pitch_task import PitchTask
    upcoming_task: UpcomingTask | None = None
    deadline = today + timedelta(days=14)
    upcoming_res = await db.execute(
        select(PitchTask).where(
            PitchTask.tenant_id == current_user.tenant_id,
            PitchTask.status != 3,
            PitchTask.bid_date >= today,
            PitchTask.bid_date <= deadline,
        ).order_by(PitchTask.bid_date.asc()).limit(1)
    )
    upcoming = upcoming_res.scalar_one_or_none()
    if upcoming and upcoming.bid_date:
        upcoming_task = UpcomingTask(
            task_id=upcoming.id,
            name=upcoming.name,
            bid_date=upcoming.bid_date,
            days_left=(upcoming.bid_date - today).days,
        )

    # ── Select practice item ──────────────────────────────────────────────────
    # If bid is ≤ 7 days away, use bid-specific countdown content (higher priority)
    bid_mode = upcoming_task is not None and upcoming_task.days_left <= 7

    if bid_mode:
        # Look for a bid_countdown type item first
        result = await db.execute(
            select(DailyPracticeItem)
            .where(
                DailyPracticeItem.practice_type == "bid_countdown",
                DailyPracticeItem.is_active.is_(True),
            )
            .limit(1)
        )
        item = result.scalar_one_or_none()
        # Fallback to weekday item if no bid_countdown item exists
        if not item:
            bid_mode = False

    if not bid_mode:
        # Normal weekday rotation
        result = await db.execute(
            select(DailyPracticeItem)
            .where(DailyPracticeItem.weekday == weekday, DailyPracticeItem.is_active.is_(True))
            .limit(1)
        )
        item = result.scalar_one_or_none()
        if not item:
            # Fallback: any active item
            result = await db.execute(
                select(DailyPracticeItem)
                .where(DailyPracticeItem.is_active.is_(True))
                .limit(1)
            )
            item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(503, "No practice content available")

    # Check if user already has a log for today
    log_result = await db.execute(
        select(DailyPracticeLog)
        .where(
            DailyPracticeLog.user_id == current_user.id,
            DailyPracticeLog.practice_date == today,
        )
        .order_by(DailyPracticeLog.id.desc())
        .limit(1)
    )
    log = log_result.scalar_one_or_none()

    # Streak
    streak = await _get_or_create_streak(current_user, db)

    # If bid_mode, personalise title/instruction with the bid name
    if bid_mode and upcoming_task:
        days_left = upcoming_task.days_left
        task_name = upcoming_task.name
        urgency = "今天" if days_left == 0 else f"还有 {days_left} 天"
        personalised_title = f"「{task_name}」述标倒计时练习（{urgency}）"
        personalised_instruction = (
            f"距「{task_name}」述标{urgency}，今天做最后冲刺练习：\n\n"
            f"1. 用 30 秒完成自我介绍 + 公司简介\n"
            f"2. 用 60 秒讲述与「{task_name}」最相关的一个成功案例\n"
            f"3. 用 30 秒预告本次方案的 1-2 个核心亮点\n\n"
            f"提示：不要死记硬背，保持自然流畅，注意眼神和语速。"
        )
        personalised_key_points = ["自我介绍", "公司简介", "案例", "方案亮点", "自然流畅"]
        personalised_duration = 120
    else:
        personalised_title = item.title
        personalised_instruction = item.instruction
        personalised_key_points = item.key_points or []
        personalised_duration = item.target_duration_sec

    return TodayPracticeResponse(
        item_id=item.id,
        practice_type="bid_countdown" if bid_mode else item.practice_type,
        title=personalised_title,
        instruction=personalised_instruction,
        target_duration_sec=personalised_duration,
        key_points=personalised_key_points,
        log_id=log.id if log else None,
        status=log.status if log else 0,
        current_streak=streak.current_streak,
        last_practice_date=streak.last_practice_date,
        upcoming_task=upcoming_task,
    )


@router.post("/start", response_model=StartPracticeResponse, status_code=201)
async def start_practice(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create/replace today's practice log and return presigned upload URL."""
    today = date.today()

    # Verify item exists
    item = await db.get(DailyPracticeItem, item_id)
    if not item or not item.is_active:
        raise HTTPException(404, "practice item not found")

    # Create log (allow re-do today)
    object_key = (
        f"{current_user.tenant_id}/pitch-coach/daily-practice/"
        f"{current_user.id}/{today.isoformat()}/{uuid.uuid4().hex}.webm"
    )
    upload_url = get_presigned_upload_url(object_key, expires_seconds=3600)

    log = DailyPracticeLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        item_id=item_id,
        practice_date=today,
        audio_url=object_key,
        status=0,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    return StartPracticeResponse(
        log_id=log.id,
        upload_url=upload_url,
        object_key=object_key,
    )


@router.post("/complete", response_model=PracticeScoreResponse)
async def complete_practice(
    body: CompletePracticeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit completed recording; compute lightweight rule-based score."""
    log = await db.get(DailyPracticeLog, body.log_id)
    if not log or log.user_id != current_user.id:
        raise HTTPException(404, "practice log not found")

    item = await db.get(DailyPracticeItem, log.item_id)
    if not item:
        raise HTTPException(404, "practice item not found")

    # Use provided transcript or empty string for scoring
    transcript = body.transcript or ""

    # --- Lightweight rule-based scoring ---
    score_result = _score_practice(
        transcript=transcript,
        duration_sec=body.audio_duration_sec,
        target_duration_sec=item.target_duration_sec,
        key_points=item.key_points or [],
    )

    # Save results
    log.audio_url = body.object_key
    log.audio_duration_sec = body.audio_duration_sec
    log.transcript = transcript
    log.total_score = score_result["total_score"]
    log.completion_ok = score_result["completion_ok"]
    log.timing_sec = body.audio_duration_sec
    log.filler_count = score_result["filler_count"]
    log.keyword_hit_rate = score_result["keyword_hit_rate"]
    log.feedback = score_result["feedback"]
    log.status = 1

    await db.commit()

    # --- Update streak ---
    streak = await _get_or_create_streak(current_user, db)
    is_new_record = False
    today = date.today()

    if streak.last_practice_date is None:
        streak.current_streak = 1
    elif streak.last_practice_date == today:
        # Already counted today
        pass
    elif streak.last_practice_date == today - timedelta(days=1):
        streak.current_streak += 1
    else:
        # Streak broken
        streak.current_streak = 1

    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak
        is_new_record = True

    streak.last_practice_date = today
    streak.total_practices += 1
    await db.commit()

    return PracticeScoreResponse(
        log_id=log.id,
        total_score=float(log.total_score),
        completion_ok=log.completion_ok,
        timing_sec=log.timing_sec,
        filler_count=log.filler_count,
        keyword_hit_rate=float(log.keyword_hit_rate),
        feedback=log.feedback or [],
        reference_answer=item.reference_answer,
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        is_new_record=is_new_record,
    )


@router.get("/history", response_model=list[PracticeHistoryItem])
async def get_practice_history(
    limit: int = 14,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return recent practice history (default last 14 days)."""
    result = await db.execute(
        select(DailyPracticeLog, DailyPracticeItem)
        .join(DailyPracticeItem, DailyPracticeLog.item_id == DailyPracticeItem.id)
        .where(DailyPracticeLog.user_id == current_user.id)
        .order_by(DailyPracticeLog.practice_date.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        PracticeHistoryItem(
            log_id=log.id,
            practice_date=log.practice_date,
            title=item.title,
            practice_type=item.practice_type,
            total_score=float(log.total_score) if log.total_score else None,
            status=log.status,
            audio_duration_sec=log.audio_duration_sec,
        )
        for log, item in rows
    ]


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    streak = await _get_or_create_streak(current_user, db)
    return StreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        total_practices=streak.total_practices,
        last_practice_date=streak.last_practice_date,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_or_create_streak(user: User, db: AsyncSession) -> UserStreak:
    streak = await db.get(UserStreak, user.id)
    if not streak:
        streak = UserStreak(user_id=user.id, tenant_id=user.tenant_id)
        db.add(streak)
        await db.flush()
    return streak


def _score_practice(
    transcript: str,
    duration_sec: int,
    target_duration_sec: int,
    key_points: list[str],
) -> dict:
    """
    Lightweight rule-based scoring (no LLM cost).

    Dimensions:
    - Timing (30%): actual vs target duration
    - Fluency (30%): filler word count
    - Completion (40%): keyword hit rate against key_points list
    """
    feedback: list[str] = []

    # 1. Timing score (30 pts)
    if duration_sec <= 0:
        timing_score = 0.0
        feedback.append("录音时长过短，请确认录音是否正常。")
    else:
        ratio = duration_sec / max(target_duration_sec, 1)
        if ratio < 0.5:
            timing_score = 40.0
            feedback.append(f"讲解时间偏短（{duration_sec}s / 目标{target_duration_sec}s），建议展开更多细节。")
        elif ratio < 0.75:
            timing_score = 70.0
            feedback.append(f"讲解时间略短，可以在关键点上多停留一些。")
        elif ratio <= 1.2:
            timing_score = 100.0
        elif ratio <= 1.5:
            timing_score = 80.0
            feedback.append(f"讲解时间略超（{duration_sec}s / 目标{target_duration_sec}s），注意把控节奏。")
        else:
            timing_score = 60.0
            feedback.append(f"讲解时间明显超时，评委可能等待，请精简内容。")

    # 2. Fluency score (30 pts) — filler word detection
    filler_count = 0
    if transcript:
        fillers = detect_filler_words(transcript)
        filler_count = len(fillers)
        if filler_count == 0:
            fluency_score = 100.0
        elif filler_count <= 2:
            fluency_score = 85.0
            feedback.append(f"有 {filler_count} 个填充词（如「那个」「嗯」），注意减少。")
        elif filler_count <= 5:
            fluency_score = 65.0
            feedback.append(f"填充词较多（{filler_count} 个），建议练习前放慢语速。")
        else:
            fluency_score = 45.0
            feedback.append(f"填充词过多（{filler_count} 个），建议先练熟稿子再录音。")
    else:
        # No transcript: assume decent fluency (can't judge)
        fluency_score = 75.0

    # 3. Completion / keyword hit rate (40 pts)
    keyword_hit_rate = 0.0
    if not key_points or not transcript:
        keyword_hit_rate = 0.5  # neutral when we can't judge
        completion_score = 75.0
        completion_ok = True
    else:
        hits = sum(1 for kw in key_points if kw.lower() in transcript.lower())
        keyword_hit_rate = hits / len(key_points)
        if keyword_hit_rate >= 0.8:
            completion_score = 100.0
            completion_ok = True
        elif keyword_hit_rate >= 0.6:
            completion_score = 80.0
            completion_ok = True
        elif keyword_hit_rate >= 0.4:
            completion_score = 60.0
            completion_ok = False
            missing = [kw for kw in key_points if kw.lower() not in transcript.lower()]
            feedback.append(f"建议补充：{' / '.join(missing[:3])}")
        else:
            completion_score = 40.0
            completion_ok = False
            missing = [kw for kw in key_points if kw.lower() not in transcript.lower()]
            feedback.append(f"遗漏了较多要点，建议补充：{' / '.join(missing[:4])}")

    # Weighted total
    total_score = round(
        timing_score * 0.30 + fluency_score * 0.30 + completion_score * 0.40,
        1
    )

    if total_score >= 85:
        feedback.insert(0, "🎉 讲解流畅！继续保持。")
    elif total_score >= 70:
        feedback.insert(0, "👍 整体不错，细节还有提升空间。")
    else:
        feedback.insert(0, "💪 继续练习，熟能生巧。")

    return {
        "total_score": total_score,
        "completion_ok": completion_ok,
        "filler_count": filler_count,
        "keyword_hit_rate": round(keyword_hit_rate, 3),
        "feedback": feedback,
    }
