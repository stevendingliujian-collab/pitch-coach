"""
F3 Training service: Ebbinghaus schedule + follow-read/recitation scoring.

跟读模式 (follow): User listens to demo narration for a page, then records themselves.
  Scores: content_alignment (text similarity), rate_match (speech rate vs demo), emphasis_hits

背诵模式 (recite): User recites from memory without reference.
  Scores: coverage_rate (key points covered), order_accuracy, naturalness (filler words)
"""
from __future__ import annotations

import difflib
import re
import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.training import TrainingPlan, TrainingSession
from app.models.pitch_task import PitchTask
from app.models.pitch_plan import PlanPage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ebbinghaus review schedule
# ---------------------------------------------------------------------------
# Intervals in days after first practice session
EBBINGHAUS_INTERVALS = [0, 1, 2, 4, 7, 15, 30]


def generate_ebbinghaus_schedule(
    first_date: date,
    bid_date: date | None,
) -> list[str]:
    """
    Generate review dates using the Ebbinghaus forgetting curve.
    Returns ISO date strings in ascending order.
    Always includes the day before bid_date (if set and within range).
    """
    dates: set[date] = set()

    for interval in EBBINGHAUS_INTERVALS:
        d = first_date + timedelta(days=interval)
        if bid_date is None or d <= bid_date:
            dates.add(d)

    # Always add the day-before-bid for final preparation
    if bid_date:
        day_before = bid_date - timedelta(days=1)
        if day_before >= first_date:
            dates.add(day_before)
        # Add bid day itself
        dates.add(bid_date)

    sorted_dates = sorted(dates)
    return [d.isoformat() for d in sorted_dates]


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _text_similarity(a: str, b: str) -> float:
    """SequenceMatcher ratio between two strings (0.0-1.0)."""
    a_clean = re.sub(r"\s+", "", a.lower())
    b_clean = re.sub(r"\s+", "", b.lower())
    if not a_clean or not b_clean:
        return 0.0
    return difflib.SequenceMatcher(None, a_clean, b_clean).ratio()


def _extract_key_phrases(text: str) -> list[str]:
    """
    Extract potential key phrases (noun phrases approximated by 2-4 char CJK chunks
    and capitalised English words).
    Used for key point matching in recite mode.
    """
    phrases: list[str] = []
    # CJK chunks of 2-4 chars
    cjk_matches = re.findall(r"[一-鿿]{2,6}", text)
    phrases.extend(cjk_matches)
    # English capitalised words / acronyms
    en_matches = re.findall(r"[A-Z][A-Za-z]{1,15}", text)
    phrases.extend(en_matches)
    return list(set(phrases))


FILLER_WORDS = ["那个", "这个", "就是", "然后", "嗯", "啊", "呃", "就", "uh", "um", "er"]


def _count_fillers(text: str) -> int:
    count = 0
    for fw in FILLER_WORDS:
        count += text.lower().count(fw)
    return count


def _chars_per_minute(text: str, duration_sec: int) -> float:
    if duration_sec <= 0:
        return 0.0
    return len(re.sub(r"\s", "", text)) / duration_sec * 60


# ---------------------------------------------------------------------------
# Follow-read scoring
# ---------------------------------------------------------------------------

def score_follow_read(
    user_transcript: str,
    reference_script: str,
    user_duration_sec: int,
    reference_duration_sec: int,
) -> dict[str, Any]:
    """
    Score a follow-read session.

    Returns:
        total_score: 0-100
        dimension_scores: {content_alignment, rate_match, emphasis_hits}
        feedback: list of improvement tips
    """
    feedback: list[str] = []

    # 1. Content alignment (0-100): text similarity to reference
    alignment = _text_similarity(user_transcript, reference_script)
    content_score = round(alignment * 100)

    if alignment < 0.5:
        feedback.append("与示范讲解内容差异较大，建议多听几遍示范音频后再练习")
    elif alignment < 0.75:
        feedback.append("有几处关键内容未能完整覆盖，重点关注加粗要点")

    # 2. Speech rate match (0-100)
    user_rate = _chars_per_minute(user_transcript, user_duration_sec)
    ref_rate = _chars_per_minute(reference_script, reference_duration_sec) if reference_duration_sec > 0 else 200.0
    ref_rate = ref_rate or 200.0

    if ref_rate > 0:
        rate_ratio = user_rate / ref_rate
        # Perfect match = 1.0; penalty for ±20% deviation
        rate_score = max(0, round(100 - abs(rate_ratio - 1.0) * 150))
    else:
        rate_score = 80

    if user_rate < 150:
        feedback.append(f"语速偏慢（{user_rate:.0f}字/分钟），建议加快至 200-250 字/分钟")
    elif user_rate > 320:
        feedback.append(f"语速偏快（{user_rate:.0f}字/分钟），听众难以跟上，建议放慢")

    # 3. Emphasis hits — check for high-value phrases from reference
    ref_phrases = _extract_key_phrases(reference_script)
    if ref_phrases:
        hits = sum(1 for p in ref_phrases if p in user_transcript)
        emphasis_score = round(min(100, hits / len(ref_phrases) * 100))
    else:
        emphasis_score = 85

    if emphasis_score < 60:
        feedback.append("部分重要术语/关键词未出现，建议重点练习这些词语的发音")

    # Weighted total: alignment 50%, rate 25%, emphasis 25%
    total_score = round(content_score * 0.5 + rate_score * 0.25 + emphasis_score * 0.25)

    if not feedback:
        feedback.append("跟读效果良好，继续保持！")

    return {
        "total_score": total_score,
        "dimension_scores": {
            "content_alignment": content_score,
            "rate_match": rate_score,
            "emphasis_hits": emphasis_score,
        },
        "feedback": feedback,
    }


# ---------------------------------------------------------------------------
# Recitation scoring
# ---------------------------------------------------------------------------

def score_recitation(
    user_transcript: str,
    talking_points: list[str],
    reference_script: str,
    user_duration_sec: int,
) -> dict[str, Any]:
    """
    Score a recitation session.

    Returns:
        total_score: 0-100
        dimension_scores: {coverage_rate, order_accuracy, naturalness}
        feedback: list of improvement tips
    """
    feedback: list[str] = []

    # 1. Coverage rate: % of talking points mentioned
    if talking_points:
        covered = []
        uncovered = []
        for tp in talking_points:
            key_phrases = _extract_key_phrases(tp)
            if key_phrases:
                hit = any(p in user_transcript for p in key_phrases)
            else:
                # fall back to 3-gram overlap
                hit = _text_similarity(tp, user_transcript) > 0.3
            if hit:
                covered.append(tp)
            else:
                uncovered.append(tp)
        coverage_rate = len(covered) / len(talking_points)
        coverage_score = round(coverage_rate * 100)
        if uncovered:
            top_missed = uncovered[:3]
            feedback.append(f"以下要点未涵盖: {', '.join(top_missed[:2])}{'等' if len(uncovered) > 2 else ''}")
    else:
        coverage_score = 80
        coverage_rate = 0.8

    # 2. Order accuracy: compare order of key phrases vs reference
    ref_phrases = _extract_key_phrases(reference_script)
    if ref_phrases and len(ref_phrases) >= 3:
        # Find positions in user transcript
        user_lower = user_transcript.lower()
        positions = [(p, user_lower.find(p.lower())) for p in ref_phrases]
        found = [(p, pos) for p, pos in positions if pos >= 0]
        if len(found) >= 2:
            sorted_by_pos = [p for p, _ in sorted(found, key=lambda x: x[1])]
            sorted_by_ref = [p for p in ref_phrases if p in [f[0] for f in found]]
            order_sim = _text_similarity(
                " ".join(sorted_by_pos), " ".join(sorted_by_ref)
            )
            order_score = round(order_sim * 100)
        else:
            order_score = 70
    else:
        order_score = 75

    if order_score < 60:
        feedback.append("内容顺序与示范讲解差异较大，建议按照讲解方案的页面顺序组织内容")

    # 3. Naturalness: penalise filler words and long silences (approximated by short transcript)
    filler_count = _count_fillers(user_transcript)
    char_count = len(re.sub(r"\s", "", user_transcript))
    filler_rate = filler_count / max(char_count / 100, 1)  # fillers per 100 chars

    if filler_rate > 3:
        naturalness_score = max(40, 100 - int(filler_rate * 10))
        feedback.append(f"填充词较多（约 {filler_count} 次），影响流畅感，尝试停顿替代口头禅")
    elif filler_rate > 1:
        naturalness_score = 85
        feedback.append("偶有填充词，整体自然度良好")
    else:
        naturalness_score = 95

    # Weighted total: coverage 50%, order 25%, naturalness 25%
    total_score = round(coverage_score * 0.5 + order_score * 0.25 + naturalness_score * 0.25)

    if not feedback:
        feedback.append("背诵效果出色，要点覆盖完整、表达自然！")

    return {
        "total_score": total_score,
        "dimension_scores": {
            "coverage_rate": coverage_score,
            "order_accuracy": order_score,
            "naturalness": naturalness_score,
        },
        "feedback": feedback,
    }


# ---------------------------------------------------------------------------
# Plan management
# ---------------------------------------------------------------------------

async def get_or_create_plan(
    user_id: int,
    tenant_id: int,
    pitch_task_id: int,
    plan_id: int | None,
    db: AsyncSession,
) -> TrainingPlan:
    """Get existing training plan or create a new one."""
    result = await db.execute(
        select(TrainingPlan).where(
            TrainingPlan.user_id == user_id,
            TrainingPlan.pitch_task_id == pitch_task_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Look up bid_date from pitch_task
    task = await db.get(PitchTask, pitch_task_id)
    bid_date = task.bid_date if task else None

    today = date.today()
    schedule = generate_ebbinghaus_schedule(today, bid_date)

    plan = TrainingPlan(
        tenant_id=tenant_id,
        user_id=user_id,
        pitch_task_id=pitch_task_id,
        plan_id=plan_id,
        first_practice_date=today,
        bid_date=bid_date,
        schedule_dates=schedule,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def get_today_plan(
    user_id: int,
    tenant_id: int,
    db: AsyncSession,
) -> list[dict]:
    """
    Return training plans that have today scheduled.
    """
    today_str = date.today().isoformat()

    result = await db.execute(
        select(TrainingPlan).where(
            TrainingPlan.user_id == user_id,
            TrainingPlan.tenant_id == tenant_id,
        )
    )
    plans = result.scalars().all()

    due_plans = []
    for plan in plans:
        schedule = plan.schedule_dates or []
        if today_str in schedule:
            # Count sessions done today for this plan
            sess_result = await db.execute(
                select(TrainingSession).where(
                    TrainingSession.plan_id == plan.id,
                    TrainingSession.practice_date == date.today(),
                )
            )
            sessions_today = sess_result.scalars().all()
            due_plans.append({
                "plan_id": plan.id,
                "pitch_task_id": plan.pitch_task_id,
                "schedule_dates": schedule,
                "sessions_done_today": len(sessions_today),
                "next_date": _next_schedule_date(schedule, today_str),
            })

    return due_plans


def _next_schedule_date(schedule: list[str], today: str) -> str | None:
    """Return the first scheduled date after today."""
    future = [d for d in schedule if d > today]
    return future[0] if future else None
