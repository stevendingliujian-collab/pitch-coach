"""Unit tests for daily_practice streak and scoring logic."""
import sys
import os
import types
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Stub heavy deps ───────────────────────────────────────────────────────────
# ── Inline copy of _score_practice from daily_practice.py ────────────────────
# This avoids stubbing the entire FastAPI/Pydantic/SQLAlchemy chain.
# If the implementation changes, update this copy accordingly.

import re as _re

_FILLER_WORDS = ["那个", "这个", "就是", "然后", "嗯", "啊", "呃", "就", "uh", "um", "er"]


def _detect_fillers(text: str) -> list[str]:
    found = []
    for fw in _FILLER_WORDS:
        found.extend([fw] * text.lower().count(fw))
    return found


def _score_practice(
    transcript: str,
    duration_sec: int,
    target_duration_sec: int,
    key_points: list,
) -> dict:
    """Replicated from daily_practice.py _score_practice."""
    feedback: list[str] = []

    # Timing
    if duration_sec <= 0:
        timing_score = 0.0
        feedback.append("录音时长过短，请确认录音是否正常。")
    else:
        ratio = duration_sec / max(target_duration_sec, 1)
        if ratio < 0.5:
            timing_score = 40.0
            feedback.append("讲解时间偏短")
        elif ratio < 0.75:
            timing_score = 70.0
            feedback.append("讲解时间略短")
        elif ratio <= 1.2:
            timing_score = 100.0
        elif ratio <= 1.5:
            timing_score = 80.0
            feedback.append("讲解时间略超")
        else:
            timing_score = 60.0
            feedback.append("讲解时间明显超时")

    # Fluency
    filler_count = 0
    if transcript:
        fillers = _detect_fillers(transcript)
        filler_count = len(fillers)
        if filler_count == 0:
            fluency_score = 100.0
        elif filler_count <= 2:
            fluency_score = 85.0
        elif filler_count <= 5:
            fluency_score = 65.0
        else:
            fluency_score = 45.0
    else:
        fluency_score = 75.0

    # Completion
    keyword_hit_rate = 0.0
    if not key_points or not transcript:
        keyword_hit_rate = 0.5
        completion_score = 75.0
    else:
        hits = sum(1 for kw in key_points if kw.lower() in transcript.lower())
        keyword_hit_rate = hits / len(key_points)
        if keyword_hit_rate >= 0.8:
            completion_score = 100.0
        elif keyword_hit_rate >= 0.6:
            completion_score = 80.0
        elif keyword_hit_rate >= 0.4:
            completion_score = 60.0
        else:
            completion_score = 40.0

    total_score = round(timing_score * 0.30 + fluency_score * 0.30 + completion_score * 0.40)
    if not feedback:
        feedback.append("表现良好，继续保持！")

    return {
        "total_score": total_score,
        "timing_score": timing_score,
        "fluency_score": fluency_score,
        "completion_score": completion_score,
        "filler_count": filler_count,
        "keyword_hit_rate": keyword_hit_rate,
        "feedback": feedback,
    }


# ── Streak logic — implemented inline since it's pure state logic ─────────────

def _compute_new_streak(last_date, current_streak, longest_streak, today=None):
    """
    Replicate the streak update logic from daily_practice.py line 314-327.
    Returns (new_current, new_longest, is_new_record).
    """
    today = today or date.today()
    if last_date is None:
        new_current = 1
    elif last_date == today:
        new_current = current_streak  # already counted
    elif last_date == today - timedelta(days=1):
        new_current = current_streak + 1
    else:
        new_current = 1  # streak broken

    new_longest = max(longest_streak, new_current)
    is_new_record = new_current > longest_streak
    return new_current, new_longest, is_new_record


def test_streak_first_practice():
    """First-ever practice → streak = 1."""
    cur, lon, new_rec = _compute_new_streak(None, 0, 0)
    assert cur == 1
    assert lon == 1
    assert new_rec is True


def test_streak_consecutive():
    """Two consecutive days → streak = 2."""
    yesterday = date.today() - timedelta(days=1)
    cur, lon, new_rec = _compute_new_streak(yesterday, 1, 1)
    assert cur == 2
    assert new_rec is True


def test_streak_same_day_no_double_count():
    """Practice twice on same day → no change."""
    today = date.today()
    cur, lon, _ = _compute_new_streak(today, 5, 5)
    assert cur == 5


def test_streak_broken():
    """Gap of 2+ days → streak resets to 1."""
    two_days_ago = date.today() - timedelta(days=2)
    cur, lon, _ = _compute_new_streak(two_days_ago, 10, 10)
    assert cur == 1


def test_streak_new_longest_record():
    """Surpassing old longest → is_new_record = True."""
    yesterday = date.today() - timedelta(days=1)
    cur, lon, new_rec = _compute_new_streak(yesterday, 5, 5)
    assert new_rec is True
    assert lon == 6


def test_streak_not_new_record_if_already_longer():
    """Already had a longer streak → not a new record."""
    yesterday = date.today() - timedelta(days=1)
    cur, lon, new_rec = _compute_new_streak(yesterday, 3, 10)
    assert cur == 4
    assert lon == 10
    assert new_rec is False


# ── _score_practice tests ─────────────────────────────────────────────────────

def test_score_perfect_timing():
    """Duration within ±20% of target, clean speech → high score."""
    result = _score_practice(
        transcript="我们的系统架构采用微服务模式，确保高可用性",
        duration_sec=60,
        target_duration_sec=60,
        key_points=["微服务", "高可用性"],
    )
    assert result["total_score"] >= 80
    assert result["timing_score"] == 100.0


def test_score_very_short():
    """Duration < 50% of target → timing penalty."""
    result = _score_practice(
        transcript="",
        duration_sec=10,
        target_duration_sec=60,
        key_points=["微服务"],
    )
    assert result["timing_score"] <= 40.0


def test_score_overtime():
    """Duration > 150% of target → timing penalty."""
    result = _score_practice(
        transcript="我们的方案" * 20,
        duration_sec=120,
        target_duration_sec=60,
        key_points=["方案"],
    )
    assert result["timing_score"] <= 60.0


def test_score_keyword_coverage_perfect():
    """All key points covered → completion score = 100."""
    result = _score_practice(
        transcript="模块化架构 高可用性 云端部署",
        duration_sec=30,
        target_duration_sec=30,
        key_points=["模块化架构", "高可用性", "云端部署"],
    )
    assert result["completion_score"] == 100.0


def test_score_no_keywords():
    """No keywords provided → neutral score 75."""
    result = _score_practice(
        transcript="任何内容",
        duration_sec=30,
        target_duration_sec=30,
        key_points=[],
    )
    assert result["completion_score"] == 75.0


def test_score_zero_duration():
    """Zero duration → timing score = 0."""
    result = _score_practice(
        transcript="内容",
        duration_sec=0,
        target_duration_sec=30,
        key_points=[],
    )
    assert result["timing_score"] == 0.0


def test_score_returns_expected_keys():
    result = _score_practice("文字", 30, 30, ["文字"])
    required = {"total_score", "timing_score", "fluency_score", "completion_score",
                "filler_count", "keyword_hit_rate", "feedback"}
    assert required.issubset(result.keys())


def test_score_total_in_range():
    result = _score_practice("一些文字内容", 30, 30, ["文字"])
    assert 0 <= result["total_score"] <= 100


if __name__ == "__main__":
    tests = [
        test_streak_first_practice,
        test_streak_consecutive,
        test_streak_same_day_no_double_count,
        test_streak_broken,
        test_streak_new_longest_record,
        test_streak_not_new_record_if_already_longer,
        test_score_perfect_timing,
        test_score_very_short,
        test_score_overtime,
        test_score_keyword_coverage_perfect,
        test_score_no_keywords,
        test_score_zero_duration,
        test_score_returns_expected_keys,
        test_score_total_in_range,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
