"""Rule-based scoring engine: 6-dimension expression analysis.

Dimensions:
  1. fluency_score   — 填充词密度 (filler words per 100 chars)
  2. rate_score      — 语速适中度 (chars per minute vs ideal range)
  3. timing_score    — 时间控制 (total duration deviation + core page ratio)
  4. originality_score — 原创性 (penalise verbatim PPT text recitation)
  5. compliance_score  — 合规风险词 (detect forbidden/risky phrases)
  6. fluency_pause_score — 卡顿检测 (long silences > 3s from ASR segments)
"""
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
class OriginalityResult:
    overlap_ratio: float   # 0-1: fraction of 4-grams shared with PPT text
    score: float           # 100 = fully original, 0 = reading PPT verbatim


@dataclass
class ComplianceResult:
    violations: list[str]  # matched risky phrase patterns
    score: float           # 100 = no violations


@dataclass
class PauseResult:
    long_pause_count: int  # silences > 3s
    score: float           # 100 = no long pauses


@dataclass
class ScoreResult:
    total_score: float
    fluency_score: float         # filler words
    rate_score: float            # speech rate
    timing_score: float          # time allocation
    originality_score: float     # (NEW) originality vs PPT
    compliance_score: float      # (NEW) compliance risk words
    pause_score: float           # (NEW) long pause detection
    filler_count: int
    filler_detail: list[dict]
    chars_per_min: float
    total_duration_sec: float
    improvement_tips: list[str]
    page_scores: list[dict]
    # Extra details
    originality_overlap_ratio: float = 0.0
    compliance_violations: list[str] = field(default_factory=list)
    long_pause_count: int = 0


def score_rehearsal(
    transcript_segments: list[dict],
    page_timings: list[dict],
    plan_pages: list[dict],
    target_duration_sec: int = 1200,
) -> ScoreResult:
    """
    6-dimension scoring.

    Args:
        transcript_segments: [{text, start, end}, ...]  from ASR
        page_timings: [{page_number, start_sec, end_sec}, ...]
        plan_pages: [{page_number, importance_level, suggested_duration_sec, content}, ...]
        target_duration_sec: planned total presentation duration
    """
    full_text = " ".join(seg.get("text", "") for seg in transcript_segments)

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
    originality = _score_originality(full_text, plan_pages)
    compliance = _score_compliance(full_text)
    pauses = _score_pauses(transcript_segments)
    page_scores = _compute_page_scores(page_timings, plan_pages, transcript_segments)

    # Weighted total: original 3 dimensions 75% + 3 new dimensions 25%
    total = round(
        filler.score * 0.25
        + rate.score * 0.20
        + timing.score * 0.30
        + originality.score * 0.10
        + compliance.score * 0.08
        + pauses.score * 0.07,
        1,
    )
    tips = _generate_tips(filler, rate, timing, originality, compliance, pauses)

    return ScoreResult(
        total_score=total,
        fluency_score=round(filler.score, 1),
        rate_score=round(rate.score, 1),
        timing_score=round(timing.score, 1),
        originality_score=round(originality.score, 1),
        compliance_score=round(compliance.score, 1),
        pause_score=round(pauses.score, 1),
        filler_count=filler.count,
        filler_detail=filler.detail,
        chars_per_min=round(rate.chars_per_min, 1),
        total_duration_sec=round(total_duration_sec, 1),
        improvement_tips=tips,
        page_scores=page_scores,
        originality_overlap_ratio=round(originality.overlap_ratio, 3),
        compliance_violations=compliance.violations,
        long_pause_count=pauses.long_pause_count,
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


def _extract_ngrams(text: str, n: int = 4) -> set[str]:
    """Extract character n-grams from text (ignoring spaces)."""
    t = re.sub(r"\s+", "", text)
    return {t[i:i+n] for i in range(len(t) - n + 1)}


def _score_originality(speech_text: str, plan_pages: list[dict]) -> OriginalityResult:
    """
    Measure how much of the speech is verbatim PPT text.
    High overlap = reading slides, penalised.
    Uses 4-gram overlap ratio.
    """
    ppt_text = " ".join(
        str(p.get("page_content_summary", p.get("content", "")) or "") + " " +
        str(p.get("key_points", "") or "") + " " +
        " ".join(
            str(tp.get("point", "") if isinstance(tp, dict) else tp)
            for tp in (p.get("talking_points") or [])
        )
        for p in plan_pages
    )
    speech_ngrams = _extract_ngrams(speech_text, 4)
    ppt_ngrams = _extract_ngrams(ppt_text, 4)

    if not speech_ngrams:
        return OriginalityResult(overlap_ratio=0.0, score=100.0)

    overlap = len(speech_ngrams & ppt_ngrams)
    ratio = overlap / len(speech_ngrams)

    # Score: 0% overlap = 100, 30% = 85, 60% = 65, 90%+ = 40
    if ratio <= 0.20:
        score = 100.0
    elif ratio <= 0.40:
        score = 90.0 - (ratio - 0.20) / 0.20 * 15
    elif ratio <= 0.70:
        score = 75.0 - (ratio - 0.40) / 0.30 * 25
    else:
        score = max(40.0, 50.0 - (ratio - 0.70) / 0.30 * 10)

    return OriginalityResult(overlap_ratio=round(ratio, 3), score=round(score, 1))


# Compliance risk patterns for 述标 context
_COMPLIANCE_PATTERNS: list[tuple[str, str]] = [
    (r"保证[一-龥]*第一|一定会赢|百分之百|必[一-龥]*中标|肯定[一-龥]*能中|必然中标|一定中标|肯定中|肯定能赢|稳赢|稳中", "投标禁语（不当承诺）"),
    (r"已经跑通|内部消息|关系[一-龥]*打点|找关系|和[一-龥]*领导[一-龥]*关系", "合规风险（暗示关系营销）"),
    (r"竞争对手[一-龥]{0,4}烂|竞争对手[一-龥]{0,4}差劲", "竞品诋毁"),
    (r"价格[一-龥]{0,4}随便|可以[一-龥]{0,4}返点|回扣", "价格合规风险"),
]
_COMPLIANCE_RE = [(re.compile(p, re.UNICODE), label) for p, label in _COMPLIANCE_PATTERNS]


def _score_compliance(text: str) -> ComplianceResult:
    """Detect compliance risk phrases. 100 = clean, deduct 15 per violation."""
    violations: list[str] = []
    for pattern, label in _COMPLIANCE_RE:
        if pattern.search(text):
            violations.append(label)
    score = max(40.0, 100.0 - len(violations) * 15)
    return ComplianceResult(violations=violations, score=score)


def _score_pauses(segments: list[dict]) -> PauseResult:
    """
    Count long silences (> 3 seconds) between ASR segments.
    More long pauses = lower score.
    """
    if len(segments) < 2:
        return PauseResult(long_pause_count=0, score=100.0)

    sorted_segs = sorted(segments, key=lambda s: s.get("start", 0))
    long_pauses = 0
    for i in range(1, len(sorted_segs)):
        gap = sorted_segs[i].get("start", 0) - sorted_segs[i - 1].get("end", 0)
        if gap > 3.0:
            long_pauses += 1

    # Score: 0 pauses = 100, 1 = 90, 3 = 70, 6+ = 50
    if long_pauses == 0:
        score = 100.0
    elif long_pauses <= 2:
        score = 90.0 - long_pauses * 5
    elif long_pauses <= 5:
        score = 80.0 - (long_pauses - 2) * 7
    else:
        score = max(50.0, 59.0 - (long_pauses - 5) * 3)

    return PauseResult(long_pause_count=long_pauses, score=round(score, 1))


def detect_filler_words(text: str) -> list[str]:
    """
    Public helper: return a flat list of filler word occurrences found in text.
    Used by daily_practice lightweight scoring.
    """
    return [m.group(0) for m in _FILLER_RE.finditer(text)]


def _generate_tips(
    filler: FillerResult,
    rate: RateResult,
    timing: TimingResult,
    originality: OriginalityResult | None = None,
    compliance: ComplianceResult | None = None,
    pauses: PauseResult | None = None,
) -> list[str]:
    tips: list[str] = []

    # Compliance violations (highest priority)
    if compliance and compliance.violations:
        for v in compliance.violations[:2]:
            tips.append(f"⚠️ 合规风险：检测到「{v}」，请调整措辞，避免触犯述标规范。")

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

    if originality and originality.overlap_ratio > 0.50:
        tips.append(f"原创性偏低（与PPT内容重合度{originality.overlap_ratio*100:.0f}%），建议用自己的语言转化讲解要点，避免照本宣科。")

    if pauses and pauses.long_pause_count > 2:
        tips.append(f"卡顿较多（{pauses.long_pause_count}处超过3秒的停顿），建议提前准备过渡语，减少语气中断。")

    if not tips:
        tips.append("整体表现良好！继续保持稳定的语速和时间控制。")

    return tips[:4]  # allow up to 4 tips with the new dimensions
