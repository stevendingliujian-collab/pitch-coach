"""Rule-based scoring engine: filler words, speech rate, timing."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Filler word patterns (Mandarin)
_FILLER_PATTERNS = [
    r"嗯+",
    r"啊+",
    r"那个",
    r"就是",
    r"然后",
    r"这个",
    r"对对",
    r"好的好的",
    r"呃+",
    r"哦+",
]
_FILLER_RE = re.compile("|".join(f"({p})" for p in _FILLER_PATTERNS))

# Ideal speech rate: 200-280 chars/min in Mandarin (述标 formal speech)
_RATE_MIN = 180
_RATE_MAX = 300
_RATE_IDEAL_LOW = 200
_RATE_IDEAL_HIGH = 260


@dataclass
class FillerResult:
    count: int
    detail: list[dict]  # [{"word": "嗯", "count": 3, "positions": [10, 45, 120]}]
    score: float        # 0-100


@dataclass
class RateResult:
    chars_per_min: float
    std_dev: float       # per-page rate standard deviation
    score: float


@dataclass
class TimingResult:
    total_duration_sec: float
    target_duration_sec: float
    deviation_ratio: float   # |actual - target| / target
    core_page_ratio: float   # time on importance>=4 pages / total
    score: float


@dataclass
class ScoreResult:
    total_score: float
    fluency_score: float     # filler words
    rate_score: float        # speech rate
    timing_score: float      # time allocation
    filler_count: int
    filler_detail: list[dict]
    chars_per_min: float
    total_duration_sec: float
    improvement_tips: list[str]
    page_scores: list[dict]


def score_rehearsal(
    transcript_segments: list[dict],
    page_timings: list[dict],
    plan_pages: list[dict],
    target_duration_sec: int = 1200,
) -> ScoreResult:
    """
    Args:
        transcript_segments: [{text, start, end}, ...]  from ASR
        page_timings: [{page_number, start_sec, end_sec}, ...]
        plan_pages: [{page_number, importance_level, suggested_duration_sec}, ...]
        target_duration_sec: planned total presentation duration
    """
    full_text = " ".join(seg.get("text", "") for seg in transcript_segments)
    total_chars = len(re.sub(r"\s+", "", full_text))

    # Determine actual total duration from page_timings
    if page_timings:
        last = max(page_timings, key=lambda x: x.get("end_sec", 0))
        total_duration_sec = float(last.get("end_sec", 0))
    else:
        total_duration_sec = sum(
            seg.get("end", 0) - seg.get("start", 0) for seg in transcript_segments
        )

    filler = _score_filler(full_text)
    rate = _score_rate(transcript_segments, page_timings, total_duration_sec)
    timing = _score_timing(page_timings, plan_pages, target_duration_sec, total_duration_sec)
    page_scores = _compute_page_scores(page_timings, plan_pages, transcript_segments)

    total = round(filler.score * 0.35 + rate.score * 0.30 + timing.score * 0.35, 1)
    tips = _generate_tips(filler, rate, timing)

    return ScoreResult(
        total_score=total,
        fluency_score=round(filler.score, 1),
        rate_score=round(rate.score, 1),
        timing_score=round(timing.score, 1),
        filler_count=filler.count,
        filler_detail=filler.detail,
        chars_per_min=round(rate.chars_per_min, 1),
        total_duration_sec=round(total_duration_sec, 1),
        improvement_tips=tips,
        page_scores=page_scores,
    )


def _score_filler(text: str) -> FillerResult:
    detail_map: dict[str, dict] = {}
    total = 0
    for m in _FILLER_RE.finditer(text):
        word = m.group(0)
        # Normalize — treat repeated chars as the base form
        base = re.sub(r"(.)\1+", r"\1", word)
        if base not in detail_map:
            detail_map[base] = {"word": base, "count": 0, "positions": []}
        detail_map[base]["count"] += 1
        detail_map[base]["positions"].append(m.start())
        total += 1

    # Score: 0 fillers = 100, 5 = 90, 15 = 70, 30+ = 40
    if total == 0:
        score = 100.0
    elif total <= 5:
        score = 90.0
    elif total <= 10:
        score = 80.0
    elif total <= 20:
        score = 70.0
    elif total <= 30:
        score = 55.0
    else:
        score = max(30.0, 55.0 - (total - 30) * 0.5)

    return FillerResult(count=total, detail=list(detail_map.values()), score=score)


def _score_rate(
    segments: list[dict],
    page_timings: list[dict],
    total_duration_sec: float,
) -> RateResult:
    if total_duration_sec <= 0:
        return RateResult(chars_per_min=0, std_dev=0, score=60.0)

    full_text = " ".join(seg.get("text", "") for seg in segments)
    total_chars = len(re.sub(r"\s+", "", full_text))
    avg_rate = total_chars / total_duration_sec * 60

    # Compute per-page rate if we have page_timings
    page_rates: list[float] = []
    if page_timings and segments:
        for pt in page_timings:
            start = pt.get("start_sec", 0)
            end = pt.get("end_sec", 0)
            dur = end - start
            if dur <= 0:
                continue
            chars = sum(
                len(re.sub(r"\s+", "", seg.get("text", "")))
                for seg in segments
                if seg.get("start", 0) >= start and seg.get("end", 0) <= end
            )
            page_rates.append(chars / dur * 60)

    std_dev = 0.0
    if len(page_rates) >= 2:
        mean = sum(page_rates) / len(page_rates)
        variance = sum((r - mean) ** 2 for r in page_rates) / len(page_rates)
        std_dev = variance ** 0.5

    # Score based on avg rate
    if _RATE_IDEAL_LOW <= avg_rate <= _RATE_IDEAL_HIGH:
        base_score = 100.0
    elif _RATE_MIN <= avg_rate < _RATE_IDEAL_LOW:
        base_score = 70.0 + (avg_rate - _RATE_MIN) / (_RATE_IDEAL_LOW - _RATE_MIN) * 30
    elif _RATE_IDEAL_HIGH < avg_rate <= _RATE_MAX:
        base_score = 70.0 + (_RATE_MAX - avg_rate) / (_RATE_MAX - _RATE_IDEAL_HIGH) * 30
    else:
        base_score = 50.0

    # Penalty for high variance (std_dev > 80 chars/min)
    variance_penalty = min(20.0, max(0.0, (std_dev - 80) / 10))
    score = max(30.0, base_score - variance_penalty)

    return RateResult(chars_per_min=avg_rate, std_dev=std_dev, score=score)


def _score_timing(
    page_timings: list[dict],
    plan_pages: list[dict],
    target_sec: int,
    actual_sec: float,
) -> TimingResult:
    if actual_sec <= 0:
        return TimingResult(0, target_sec, 1.0, 0.0, 50.0)

    deviation = abs(actual_sec - target_sec) / target_sec

    # Core page ratio (importance >= 4)
    core_page_nums = {
        p["page_number"] for p in plan_pages if p.get("importance_level", 3) >= 4
    }
    if core_page_nums and page_timings:
        core_time = sum(
            (pt.get("end_sec", 0) - pt.get("start_sec", 0))
            for pt in page_timings
            if pt.get("page_number") in core_page_nums
        )
        core_ratio = core_time / actual_sec if actual_sec > 0 else 0
    else:
        core_ratio = 0.6  # assume OK if no data

    # Score: deviation within 10% = 100, 20% = 80, 30% = 60, 50%+ = 40
    if deviation <= 0.10:
        dev_score = 100.0
    elif deviation <= 0.20:
        dev_score = 80.0 + (0.20 - deviation) / 0.10 * 20
    elif deviation <= 0.30:
        dev_score = 60.0 + (0.30 - deviation) / 0.10 * 20
    else:
        dev_score = max(30.0, 60.0 - (deviation - 0.30) * 100)

    # Core ratio bonus/penalty
    if core_ratio >= 0.60:
        ratio_score = 100.0
    elif core_ratio >= 0.45:
        ratio_score = 70.0 + (core_ratio - 0.45) / 0.15 * 30
    else:
        ratio_score = max(40.0, core_ratio / 0.45 * 70)

    score = dev_score * 0.6 + ratio_score * 0.4
    return TimingResult(
        total_duration_sec=actual_sec,
        target_duration_sec=target_sec,
        deviation_ratio=round(deviation, 3),
        core_page_ratio=round(core_ratio, 3),
        score=round(score, 1),
    )


def _compute_page_scores(
    page_timings: list[dict],
    plan_pages: list[dict],
    segments: list[dict],
) -> list[dict]:
    plan_map = {p["page_number"]: p for p in plan_pages}
    result = []
    for pt in page_timings:
        pn = pt.get("page_number", 0)
        start = pt.get("start_sec", 0)
        end = pt.get("end_sec", 0)
        dur = end - start
        plan = plan_map.get(pn, {})
        suggested = plan.get("suggested_duration_sec", 0)
        deviation = abs(dur - suggested) / max(suggested, 1)
        timing_ok = deviation <= 0.25
        result.append({
            "page_number": pn,
            "actual_duration_sec": round(dur, 1),
            "suggested_duration_sec": suggested,
            "timing_ok": timing_ok,
            "importance_level": plan.get("importance_level", 3),
        })
    return result


def _generate_tips(filler: FillerResult, rate: RateResult, timing: TimingResult) -> list[str]:
    tips: list[str] = []

    if filler.count > 15:
        worst = sorted(filler.detail, key=lambda x: x["count"], reverse=True)[:2]
        words = "、".join(f'"{d["word"]}"' for d in worst)
        tips.append(f"填充词过多（共{filler.count}次），尤其是{words}，建议刻意练习停顿替代填充词。")
    elif filler.count > 5:
        tips.append(f"注意填充词（共{filler.count}次），在换气时保持短暂停顿，不要用填充词过渡。")

    if rate.chars_per_min < _RATE_IDEAL_LOW:
        tips.append(f"语速偏慢（{rate.chars_per_min:.0f}字/分钟），建议适当提速至200-260字/分钟。")
    elif rate.chars_per_min > _RATE_IDEAL_HIGH:
        tips.append(f"语速偏快（{rate.chars_per_min:.0f}字/分钟），建议放慢至200-260字/分钟，确保评委跟上节奏。")

    dev_pct = timing.deviation_ratio * 100
    if timing.deviation_ratio > 0.20:
        direction = "超时" if timing.total_duration_sec > timing.target_duration_sec else "未用完"
        tips.append(f"时间控制偏差{dev_pct:.0f}%（{direction}），请严格按计划时长练习。")

    if timing.core_page_ratio < 0.55:
        tips.append(f"核心页面时间占比仅{timing.core_page_ratio*100:.0f}%，低于建议的60%，注意重点内容的时间分配。")

    if not tips:
        tips.append("整体表现良好！继续保持稳定的语速和时间控制。")

    return tips[:3]
