"""Unit tests for training_service — pure-logic functions, no DB required."""
import sys
import os
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Stub heavy deps ───────────────────────────────────────────────────────────
_STUB_MODS = [
    "sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext", "sqlalchemy.ext.asyncio",
    "app.models.training", "app.models.pitch_task", "app.models.pitch_plan",
]
for _mod in _STUB_MODS:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

for _attr in ("select", "Column", "Integer", "String", "Boolean", "DateTime",
              "Text", "ForeignKey", "func", "and_", "or_"):
    for _ns in ("sqlalchemy", "sqlalchemy.orm"):
        m = sys.modules[_ns]
        if not hasattr(m, _attr):
            setattr(m, _attr, lambda *a, **kw: None)

_asyncio_mod = sys.modules["sqlalchemy.ext.asyncio"]
if not hasattr(_asyncio_mod, "AsyncSession"):
    class _AsyncSession: pass
    _asyncio_mod.AsyncSession = _AsyncSession  # type: ignore

for _name in ("TrainingPlan", "TrainingSession"):
    setattr(sys.modules["app.models.training"], _name, type(_name, (), {}))
for _name in ("PitchTask",):
    setattr(sys.modules["app.models.pitch_task"], _name, type(_name, (), {}))
for _name in ("PlanPage",):
    setattr(sys.modules["app.models.pitch_plan"], _name, type(_name, (), {}))

# ── Actual imports ────────────────────────────────────────────────────────────
from datetime import date, timedelta
from app.services.training_service import (
    generate_ebbinghaus_schedule,
    score_follow_read,
    score_recitation,
    _text_similarity,
    _extract_key_phrases,
    _count_fillers,
    _chars_per_minute,
)


# ── Ebbinghaus schedule tests ─────────────────────────────────────────────────

def test_ebbinghaus_basic_intervals():
    """Should produce dates at 0,1,2,4,7,15,30 days plus day-before-bid."""
    start = date(2026, 6, 1)
    bid = date(2026, 7, 31)   # far enough that all intervals fit
    schedule = generate_ebbinghaus_schedule(start, bid)
    assert schedule[0] == start.isoformat()           # Day 0
    assert (start + timedelta(days=1)).isoformat() in schedule
    assert (start + timedelta(days=4)).isoformat() in schedule
    assert (start + timedelta(days=7)).isoformat() in schedule
    assert (start + timedelta(days=15)).isoformat() in schedule


def test_ebbinghaus_includes_day_before_bid():
    start = date(2026, 6, 1)
    bid = date(2026, 6, 20)
    schedule = generate_ebbinghaus_schedule(start, bid)
    day_before = (bid - timedelta(days=1)).isoformat()
    assert day_before in schedule
    assert bid.isoformat() in schedule


def test_ebbinghaus_no_bid_date():
    """Without bid date all standard intervals are included."""
    start = date(2026, 6, 1)
    schedule = generate_ebbinghaus_schedule(start, None)
    assert len(schedule) == len(set(schedule))  # no duplicates
    assert (start + timedelta(days=30)).isoformat() in schedule


def test_ebbinghaus_bid_soon():
    """Bid date close to start — only fitting intervals included."""
    start = date(2026, 6, 1)
    bid = date(2026, 6, 5)   # 4 days out
    schedule = generate_ebbinghaus_schedule(start, bid)
    # day-30 should NOT be in schedule (beyond bid)
    assert (start + timedelta(days=30)).isoformat() not in schedule
    # day-0 through day-4 should be there
    assert start.isoformat() in schedule
    assert (start + timedelta(days=4)).isoformat() in schedule


def test_ebbinghaus_sorted():
    start = date(2026, 6, 1)
    bid = date(2026, 7, 15)
    schedule = generate_ebbinghaus_schedule(start, bid)
    assert schedule == sorted(schedule)


# ── Text similarity tests ─────────────────────────────────────────────────────

def test_text_similarity_identical():
    assert _text_similarity("你好世界", "你好世界") == 1.0


def test_text_similarity_empty():
    assert _text_similarity("", "任何文字") == 0.0
    assert _text_similarity("任何文字", "") == 0.0


def test_text_similarity_partial():
    s = _text_similarity("今天天气好", "今天")
    assert 0.0 < s < 1.0


def test_text_similarity_unrelated():
    s = _text_similarity("我们的方案非常出色", "橙汁大杯加冰")
    assert s < 0.5


# ── Key phrase extraction ─────────────────────────────────────────────────────

def test_extract_key_phrases_cjk():
    phrases = _extract_key_phrases("采用模块化架构和分布式设计")
    assert len(phrases) > 0
    # Every phrase should be ≥2 chars
    assert all(len(p) >= 2 for p in phrases)


def test_extract_key_phrases_english():
    phrases = _extract_key_phrases("Our AI platform uses BERT model")
    assert "AI" in phrases or "BERT" in phrases or "Our" in phrases


def test_extract_key_phrases_empty():
    assert _extract_key_phrases("") == []


# ── Filler counter ────────────────────────────────────────────────────────────

def test_count_fillers_none():
    assert _count_fillers("今天展示的是我们的核心方案") == 0


def test_count_fillers_multiple():
    text = "嗯，这个，那个，然后，就是，我们的方案啊"
    count = _count_fillers(text)
    assert count >= 4


# ── Chars per minute ──────────────────────────────────────────────────────────

def test_chars_per_minute_normal():
    text = "测" * 100   # 100 chars
    cpm = _chars_per_minute(text, 30)   # 30s = 200 chars/min
    assert abs(cpm - 200.0) < 1


def test_chars_per_minute_zero_duration():
    assert _chars_per_minute("test", 0) == 0.0


# ── Follow-read scoring ───────────────────────────────────────────────────────

def test_follow_read_perfect():
    script = "我们采用业界领先的云原生架构，确保高可用性和可扩展性"
    result = score_follow_read(
        user_transcript=script,
        reference_script=script,
        user_duration_sec=10,
        reference_duration_sec=10,
    )
    assert result["total_score"] >= 90
    assert result["dimension_scores"]["content_alignment"] >= 95


def test_follow_read_low_similarity():
    reference = "我们的核心系统采用微服务架构，部署在云端"
    user = "今天天气不错"
    result = score_follow_read(
        user_transcript=user,
        reference_script=reference,
        user_duration_sec=5,
        reference_duration_sec=10,
    )
    assert result["total_score"] < 50
    assert any("差异" in tip or "示范" in tip for tip in result["feedback"])


def test_follow_read_slow_rate():
    """User takes 3× longer than reference → rate penalty."""
    script = "测" * 100
    result = score_follow_read(
        user_transcript=script,
        reference_script=script,
        user_duration_sec=120,   # very slow: ~50 chars/min
        reference_duration_sec=30,
    )
    assert result["dimension_scores"]["rate_match"] < 80


def test_follow_read_has_feedback():
    result = score_follow_read("好", "我们具有核心竞争优势和创新能力", 3, 5)
    assert isinstance(result["feedback"], list)
    assert len(result["feedback"]) >= 1


def test_follow_read_score_range():
    result = score_follow_read(
        "我们展示方案的优势",
        "我们的方案具有明显竞争优势",
        user_duration_sec=5,
        reference_duration_sec=5,
    )
    assert 0 <= result["total_score"] <= 100
    for v in result["dimension_scores"].values():
        assert 0 <= v <= 100


# ── Recitation scoring ────────────────────────────────────────────────────────

def test_recitation_covers_all_points():
    talking_points = ["模块化架构", "高可用性", "云端部署"]
    user = "我们采用模块化架构，保证高可用性，全部服务云端部署"
    result = score_recitation(
        user_transcript=user,
        talking_points=talking_points,
        reference_script=user,
        user_duration_sec=10,
    )
    assert result["total_score"] >= 80
    assert result["dimension_scores"]["coverage_rate"] >= 80


def test_recitation_misses_points():
    talking_points = ["模块化架构", "人工智能", "大数据分析", "边缘计算"]
    user = "今天天气很好"
    result = score_recitation(
        user_transcript=user,
        talking_points=talking_points,
        reference_script="模块化架构 人工智能 大数据分析 边缘计算",
        user_duration_sec=5,
    )
    assert result["dimension_scores"]["coverage_rate"] < 50


def test_recitation_naturalness_with_fillers():
    """Many filler words → naturalness penalty."""
    talking_points = ["云端部署"]
    user = "嗯，那个，就是，然后，我们，嗯嗯，那个，云端部署，啊，就是"
    result = score_recitation(
        user_transcript=user,
        talking_points=talking_points,
        reference_script="我们的服务云端部署",
        user_duration_sec=15,
    )
    assert result["dimension_scores"]["naturalness"] < 80


def test_recitation_empty_talking_points():
    """No talking points → coverage defaults gracefully."""
    result = score_recitation(
        user_transcript="我们介绍一下核心方案的优势",
        talking_points=[],
        reference_script="核心方案优势介绍",
        user_duration_sec=8,
    )
    assert 0 <= result["total_score"] <= 100


def test_recitation_returns_feedback():
    result = score_recitation(
        user_transcript="介绍方案",
        talking_points=["核心技术", "市场优势", "团队实力"],
        reference_script="核心技术 市场优势 团队实力",
        user_duration_sec=5,
    )
    assert isinstance(result["feedback"], list)
    assert len(result["feedback"]) >= 1


if __name__ == "__main__":
    tests = [
        test_ebbinghaus_basic_intervals,
        test_ebbinghaus_includes_day_before_bid,
        test_ebbinghaus_no_bid_date,
        test_ebbinghaus_bid_soon,
        test_ebbinghaus_sorted,
        test_text_similarity_identical,
        test_text_similarity_empty,
        test_text_similarity_partial,
        test_text_similarity_unrelated,
        test_extract_key_phrases_cjk,
        test_extract_key_phrases_english,
        test_extract_key_phrases_empty,
        test_count_fillers_none,
        test_count_fillers_multiple,
        test_chars_per_minute_normal,
        test_chars_per_minute_zero_duration,
        test_follow_read_perfect,
        test_follow_read_low_similarity,
        test_follow_read_slow_rate,
        test_follow_read_has_feedback,
        test_follow_read_score_range,
        test_recitation_covers_all_points,
        test_recitation_misses_points,
        test_recitation_naturalness_with_fillers,
        test_recitation_empty_talking_points,
        test_recitation_returns_feedback,
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
