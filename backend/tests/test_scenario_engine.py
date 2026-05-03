"""Unit tests for scenario_engine — pure-logic functions, no LLM/DB required."""
import sys
import os
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Stub async/LLM deps ───────────────────────────────────────────────────────
_STUB_MODS = [
    "sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext", "sqlalchemy.ext.asyncio",
    "app.services.llm_adapter", "app.services.asr_adapter",
]
for _mod in _STUB_MODS:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

for _attr in ("select", "update", "delete", "insert", "text", "Column", "Integer", "BigInteger", "SmallInteger", "String", "Boolean", "DateTime", "Date", "Text", "Float", "Numeric", "JSON", "JSONB", "ARRAY", "ForeignKey", "func", "and_", "or_", "not_", "case", "cast", "UniqueConstraint", "Index", "CheckConstraint", "PrimaryKeyConstraint", "relationship", "backref", "mapped_column", "Mapped", "DeclarativeBase", "declared_attr"):
    for _ns in ("sqlalchemy", "sqlalchemy.orm"):
        m = sys.modules[_ns]
        if not hasattr(m, _attr):
            setattr(m, _attr, lambda *a, **kw: None)

_asyncio_mod = sys.modules["sqlalchemy.ext.asyncio"]
if not hasattr(_asyncio_mod, "AsyncSession"):
    class _AsyncSession: pass
    _asyncio_mod.AsyncSession = _AsyncSession  # type: ignore

# Stub call_llm
_llm_mod = sys.modules["app.services.llm_adapter"]
async def _fake_llm(*a, **kw): return "stub response"
_llm_mod.call_llm = _fake_llm  # type: ignore

# Stub asr_adapter with _stub_transcribe so test_e2e_p1 can import it
_asr_mod = sys.modules["app.services.asr_adapter"]
def _stub_transcribe(audio_bytes: bytes):
    return [{"text": "stub transcript", "start": 0.0, "end": 1.0}]
_asr_mod._stub_transcribe = _stub_transcribe  # type: ignore
_asr_mod.transcribe = lambda *a, **kw: None  # type: ignore

from app.services.scenario_engine import (
    calculate_adaptive_difficulty,
    get_difficulty_label,
    get_scenario,
    list_scenarios,
    PRESET_SCENARIOS,
)


# ── Scenario catalogue sanity ─────────────────────────────────────────────────

def test_scenarios_present():
    """At least 30 preset scenarios should exist."""
    assert len(PRESET_SCENARIOS) >= 30


def test_scenarios_have_required_fields():
    required = {"id", "name", "industry", "difficulty", "customer_type"}
    for s in PRESET_SCENARIOS:
        missing = required - s.keys()
        assert not missing, f"Scenario {s.get('id')} missing: {missing}"


def test_scenario_ids_unique():
    ids = [s["id"] for s in PRESET_SCENARIOS]
    assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"


def test_scenario_difficulty_range():
    for s in PRESET_SCENARIOS:
        assert 1 <= s["difficulty"] <= 5, f"Scenario {s['id']} difficulty out of range"


def test_scenarios_cover_multiple_industries():
    industries = {s["industry"] for s in PRESET_SCENARIOS}
    assert len(industries) >= 3, f"Expected ≥3 industries, got {industries}"


# ── get_scenario ──────────────────────────────────────────────────────────────

def test_get_scenario_existing():
    first_id = PRESET_SCENARIOS[0]["id"]
    s = get_scenario(first_id)
    assert s is not None
    assert s["id"] == first_id


def test_get_scenario_nonexistent():
    assert get_scenario("nonexistent-scenario-xyz") is None


# ── list_scenarios ────────────────────────────────────────────────────────────

def test_list_all_scenarios():
    all_s = list_scenarios()
    assert len(all_s) == len(PRESET_SCENARIOS)


def test_list_by_industry():
    # Pick any industry that exists
    first_industry = PRESET_SCENARIOS[0]["industry"]
    filtered = list_scenarios(industry=first_industry)
    assert all(s["industry"] == first_industry for s in filtered)
    assert len(filtered) >= 1


def test_list_by_difficulty():
    # Level 3 should have several scenarios
    filtered = list_scenarios(difficulty=3)
    assert all(s["difficulty"] == 3 for s in filtered)


def test_list_by_industry_and_difficulty():
    # Combined filter should be subset of each individual filter
    first_industry = PRESET_SCENARIOS[0]["industry"]
    combined = list_scenarios(industry=first_industry, difficulty=3)
    by_industry = list_scenarios(industry=first_industry)
    assert len(combined) <= len(by_industry)


def test_list_empty_for_unknown_industry():
    result = list_scenarios(industry="nonexistent_industry_xyz")
    assert result == []


# ── calculate_adaptive_difficulty ────────────────────────────────────────────

def test_difficulty_increases_on_high_scores():
    """Two consecutive scores ≥80 → difficulty +1."""
    new_diff = calculate_adaptive_difficulty([85, 90], current_difficulty=2)
    assert new_diff == 3


def test_difficulty_decreases_on_low_scores():
    """Two consecutive scores <50 → difficulty -1."""
    new_diff = calculate_adaptive_difficulty([40, 45], current_difficulty=3)
    assert new_diff == 2


def test_difficulty_unchanged_on_mixed():
    """Mixed scores → no change."""
    new_diff = calculate_adaptive_difficulty([85, 40], current_difficulty=3)
    assert new_diff == 3


def test_difficulty_max_cap():
    """Already at 5 → can't go higher."""
    new_diff = calculate_adaptive_difficulty([90, 95], current_difficulty=5)
    assert new_diff == 5


def test_difficulty_min_cap():
    """Already at 1 → can't go lower."""
    new_diff = calculate_adaptive_difficulty([30, 20], current_difficulty=1)
    assert new_diff == 1


def test_difficulty_insufficient_data():
    """Less than 2 scores → unchanged."""
    new_diff = calculate_adaptive_difficulty([90], current_difficulty=3)
    assert new_diff == 3
    new_diff2 = calculate_adaptive_difficulty([], current_difficulty=2)
    assert new_diff2 == 2


# ── get_difficulty_label ──────────────────────────────────────────────────────

def test_difficulty_labels():
    assert get_difficulty_label(1) == "入门"
    assert get_difficulty_label(2) == "基础"
    assert get_difficulty_label(3) == "进阶"
    assert get_difficulty_label(4) == "挑战"
    assert get_difficulty_label(5) == "专家"


def test_difficulty_label_fallback():
    # Unknown level → fallback
    label = get_difficulty_label(99)
    assert isinstance(label, str) and len(label) > 0


if __name__ == "__main__":
    tests = [
        test_scenarios_present,
        test_scenarios_have_required_fields,
        test_scenario_ids_unique,
        test_scenario_difficulty_range,
        test_scenarios_cover_multiple_industries,
        test_get_scenario_existing,
        test_get_scenario_nonexistent,
        test_list_all_scenarios,
        test_list_by_industry,
        test_list_by_difficulty,
        test_list_by_industry_and_difficulty,
        test_list_empty_for_unknown_industry,
        test_difficulty_increases_on_high_scores,
        test_difficulty_decreases_on_low_scores,
        test_difficulty_unchanged_on_mixed,
        test_difficulty_max_cap,
        test_difficulty_min_cap,
        test_difficulty_insufficient_data,
        test_difficulty_labels,
        test_difficulty_label_fallback,
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
