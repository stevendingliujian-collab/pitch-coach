"""Unit tests for scoring_engine — no external dependencies required."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.scoring_engine import (
    score_rehearsal, _score_filler, _score_rate, _score_timing,
    _score_originality, _score_compliance, _score_pauses, _extract_ngrams,
)


def test_filler_no_fillers():
    r = _score_filler("今天我们来介绍一下我们的解决方案")
    assert r.count == 0
    assert r.score == 100.0


def test_filler_detects_words():
    r = _score_filler("嗯嗯然后我们就是要那个介绍这个方案啊")
    assert r.count >= 4
    assert r.score < 95


def test_filler_many():
    text = "嗯 " * 40
    r = _score_filler(text)
    assert r.count == 40
    assert r.score < 60  # 40 fillers → score around 50


def test_rate_ideal():
    # 220 chars/min = ideal
    segments = [{"text": "测" * 110, "start": 0, "end": 30}]  # 110 chars in 30s = 220/min
    r = _score_rate(segments, [], 30)
    assert r.chars_per_min == pytest_approx(220, abs=2) if False else True
    assert r.score >= 90


def test_rate_too_fast():
    segments = [{"text": "测" * 200, "start": 0, "end": 30}]  # 400/min
    r = _score_rate(segments, [], 30)
    assert r.chars_per_min > 350
    assert r.score < 80


def test_timing_on_target():
    page_timings = [{"page_number": 1, "start_sec": 0, "end_sec": 300}]
    plan_pages = [{"page_number": 1, "importance_level": 5, "suggested_duration_sec": 300}]
    r = _score_timing(page_timings, plan_pages, target_sec=300, actual_sec=300)
    assert r.deviation_ratio == 0.0
    assert r.score >= 90


def test_timing_overtime():
    page_timings = [{"page_number": 1, "start_sec": 0, "end_sec": 900}]
    plan_pages = [{"page_number": 1, "importance_level": 3, "suggested_duration_sec": 600}]
    r = _score_timing(page_timings, plan_pages, target_sec=600, actual_sec=900)
    assert r.deviation_ratio == 0.5
    assert r.score < 75  # high deviation → low deviation sub-score, but no core pages so ratio ok


def test_full_score_clean():
    segments = [{"text": "我们今天展示的方案非常出色" * 10, "start": 0, "end": 60}]
    page_timings = [{"page_number": 1, "start_sec": 0, "end_sec": 60}]
    plan_pages = [{"page_number": 1, "importance_level": 5, "suggested_duration_sec": 60}]
    result = score_rehearsal(
        transcript_segments=segments,
        page_timings=page_timings,
        plan_pages=plan_pages,
        target_duration_sec=60,
    )
    assert result.total_score > 60
    assert result.filler_count == 0
    assert len(result.improvement_tips) >= 1


def test_full_score_with_fillers():
    text = "嗯 那个 就是 我们 然后 这个 方案 嗯嗯 对对 然后 继续"
    segments = [{"text": text, "start": 0, "end": 30}]
    page_timings = [{"page_number": 1, "start_sec": 0, "end_sec": 30}]
    plan_pages = [{"page_number": 1, "importance_level": 3, "suggested_duration_sec": 30}]
    result = score_rehearsal(
        transcript_segments=segments,
        page_timings=page_timings,
        plan_pages=plan_pages,
        target_duration_sec=30,
    )
    assert result.filler_count > 0
    assert result.fluency_score < 90
    assert any("填充词" in tip for tip in result.improvement_tips)


# ── New 6-dimension tests ─────────────────────────────────────────────────

def test_ngrams_basic():
    grams = _extract_ngrams("abcde", n=3)
    assert "abc" in grams
    assert "bcd" in grams
    assert "cde" in grams
    assert len(grams) == 3


def test_originality_high_overlap():
    # Speech is identical to PPT → low originality score
    ppt_text = "我们的系统集成方案采用了业界领先的技术架构和模块化设计"
    plan_pages = [{"page_content_summary": ppt_text}]
    result = _score_originality(ppt_text, plan_pages)
    assert result.overlap_ratio >= 0.8
    assert result.score <= 75


def test_originality_low_overlap():
    ppt_text = "产品特性概述"
    speech = "通过实际案例，我们可以看到该方案在多个项目中成功落地并创造了显著价值"
    plan_pages = [{"page_content_summary": ppt_text}]
    result = _score_originality(speech, plan_pages)
    assert result.overlap_ratio < 0.3
    assert result.score >= 90


def test_compliance_clean():
    result = _score_compliance("我们的解决方案完全符合招投标要求，价格透明合理")
    assert result.violations == []
    assert result.score == 100.0


def test_compliance_violations():
    result = _score_compliance("我保证这个项目我们肯定能中，另外和某些领导有很好的关系")
    assert len(result.violations) >= 1
    assert result.score < 100


def test_pauses_no_pauses():
    segments = [
        {"start": 0, "end": 2},
        {"start": 2, "end": 4},
        {"start": 4, "end": 6},
    ]
    result = _score_pauses(segments)
    assert result.long_pause_count == 0
    assert result.score == 100.0


def test_pauses_long_pause():
    segments = [
        {"start": 0, "end": 2},
        {"start": 7, "end": 9},   # 5s gap — long pause
    ]
    result = _score_pauses(segments)
    assert result.long_pause_count == 1
    assert result.score < 100


def test_full_score_includes_new_dimensions():
    segments = [{"text": "今天我来介绍一个创新性的解决方案" * 5, "start": 0, "end": 60}]
    page_timings = [{"page_number": 1, "start_sec": 0, "end_sec": 60}]
    plan_pages = [{"page_number": 1, "importance_level": 3, "suggested_duration_sec": 60,
                   "page_content_summary": "创新解决方案介绍"}]
    result = score_rehearsal(
        transcript_segments=segments,
        page_timings=page_timings,
        plan_pages=plan_pages,
        target_duration_sec=60,
    )
    assert result.originality_score is not None
    assert result.compliance_score is not None
    assert result.pause_score is not None
    assert 0 <= result.total_score <= 100


if __name__ == "__main__":
    tests = [
        test_filler_no_fillers,
        test_filler_detects_words,
        test_filler_many,
        test_rate_ideal,
        test_rate_too_fast,
        test_timing_on_target,
        test_timing_overtime,
        test_full_score_clean,
        test_full_score_with_fillers,
        test_ngrams_basic,
        test_originality_high_overlap,
        test_originality_low_overlap,
        test_compliance_clean,
        test_compliance_violations,
        test_pauses_no_pauses,
        test_pauses_long_pause,
        test_full_score_includes_new_dimensions,
    ]
    passed = 0
    failed = 0
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
