"""Unit tests for rubric_engine — pure-logic functions, no LLM/DB required."""
import sys
import os
import types
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Stub heavy deps ───────────────────────────────────────────────────────────
_STUB_MODS = [
    "sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext", "sqlalchemy.ext.asyncio",
    "app.services.llm_adapter",
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
    class _AS: pass
    _asyncio_mod.AsyncSession = _AS  # type: ignore

async def _fake_llm(*a, **kw): return '{"scores":[],"improvement_suggestions":[]}'
sys.modules["app.services.llm_adapter"].call_llm = _fake_llm  # type: ignore

from app.services.rubric_engine import (
    get_preset_templates,
    compute_rubric_total,
    _parse_llm_json,
    PRESET_TEMPLATES,
)


# ── Preset template catalogue ─────────────────────────────────────────────────

def test_preset_templates_present():
    templates = get_preset_templates()
    assert len(templates) >= 3, "Expected at least 3 preset templates"


def test_preset_templates_have_required_fields():
    required = {"name", "template_type", "items"}
    for t in PRESET_TEMPLATES:
        missing = required - t.keys()
        assert not missing, f"Template '{t.get('name')}' missing: {missing}"


def test_preset_template_items_have_scores():
    for t in PRESET_TEMPLATES:
        for item in t.get("items", []):
            assert "max_score" in item, f"Item missing max_score: {item}"
            assert float(item["max_score"]) > 0


def test_preset_template_total_score_reasonable():
    """Each template's total max score should be between 50 and 200."""
    for t in PRESET_TEMPLATES:
        total = compute_rubric_total(t.get("items", []))
        assert 50 <= total <= 200, f"Template '{t['name']}' total {total} out of range"


def test_preset_templates_cover_system_integration():
    names = [t.get("template_type", t.get("name", "")) for t in PRESET_TEMPLATES]
    has_si = any("system" in n.lower() or "集成" in n for n in names)
    assert has_si, f"Expected system_integration template, got: {names}"


# ── compute_rubric_total ──────────────────────────────────────────────────────

def test_compute_total_basic():
    items = [{"max_score": 10}, {"max_score": 20}, {"max_score": 30}]
    assert compute_rubric_total(items) == 60.0


def test_compute_total_empty():
    assert compute_rubric_total([]) == 0.0


def test_compute_total_float_scores():
    items = [{"max_score": "10.5"}, {"max_score": "9.5"}]
    assert compute_rubric_total(items) == 20.0


def test_compute_total_missing_score_defaults_zero():
    items = [{"name": "item without score"}, {"max_score": 15}]
    assert compute_rubric_total(items) == 15.0


# ── _parse_llm_json ───────────────────────────────────────────────────────────

def test_parse_clean_json():
    raw = '{"scores": [{"item_id": "1", "score": 8}], "improvement_suggestions": []}'
    result = _parse_llm_json(raw)
    assert result["scores"][0]["score"] == 8


def test_parse_json_with_markdown_fences():
    raw = '```json\n{"scores": [], "overall_comments": "好"}\n```'
    result = _parse_llm_json(raw)
    assert result["overall_comments"] == "好"


def test_parse_json_with_surrounding_text():
    raw = 'Here is the evaluation:\n{"scores": [{"item_id": "2", "score": 7}]}\nEnd.'
    result = _parse_llm_json(raw)
    assert result["scores"][0]["item_id"] == "2"


def test_parse_invalid_json_returns_fallback():
    raw = "This is not JSON at all"
    result = _parse_llm_json(raw)
    assert result == {"scores": [], "improvement_suggestions": []}


def test_parse_empty_string_returns_fallback():
    result = _parse_llm_json("")
    assert "scores" in result


def test_parse_malformed_json_returns_fallback():
    raw = '{"scores": [broken json'
    result = _parse_llm_json(raw)
    assert result == {"scores": [], "improvement_suggestions": []}


if __name__ == "__main__":
    tests = [
        test_preset_templates_present,
        test_preset_templates_have_required_fields,
        test_preset_template_items_have_scores,
        test_preset_template_total_score_reasonable,
        test_preset_templates_cover_system_integration,
        test_compute_total_basic,
        test_compute_total_empty,
        test_compute_total_float_scores,
        test_compute_total_missing_score_defaults_zero,
        test_parse_clean_json,
        test_parse_json_with_markdown_fences,
        test_parse_json_with_surrounding_text,
        test_parse_invalid_json_returns_fallback,
        test_parse_empty_string_returns_fallback,
        test_parse_malformed_json_returns_fallback,
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
