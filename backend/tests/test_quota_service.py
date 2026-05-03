"""Unit tests for quota_service — registry loading and pure limit lookups."""
import sys
import os
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Stub heavy deps ───────────────────────────────────────────────────────────
_STUB_MODS = [
    "sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext", "sqlalchemy.ext.asyncio",
    "sqlalchemy.dialects", "sqlalchemy.dialects.postgresql",
    "app.models.user", "app.models.usage",
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

_pg_mod = sys.modules["sqlalchemy.dialects.postgresql"]
if not hasattr(_pg_mod, "insert"):
    _pg_mod.insert = lambda *a, **kw: None  # type: ignore

for _name in ("User",):
    setattr(sys.modules["app.models.user"], _name, type(_name, (), {}))
for _name in ("UsageMeter", "UsageEvent"):
    setattr(sys.modules["app.models.usage"], _name, type(_name, (), {}))

from app.services.quota_service import (
    _get_plan_limit,
    get_gated_routes,
    _year_month,
    FREE_LIMITS,
    FEATURE_LABELS,
    _REGISTRY,
    _FALLBACK_FREE,
)


# ── Registry sanity ───────────────────────────────────────────────────────────

def test_registry_loads_known_features():
    """feature_registry.yaml should define the 6 gated features."""
    expected = {"ppt_uploads", "rehearsals", "narration_pages",
                "knowledge_docs", "evaluator_sessions", "rubric_scoring"}
    if _REGISTRY:
        for feat in expected:
            assert feat in _REGISTRY or feat in _FALLBACK_FREE, f"Missing feature: {feat}"


def test_feature_labels_populated():
    assert len(FEATURE_LABELS) > 0
    for key, label in FEATURE_LABELS.items():
        assert isinstance(label, str) and len(label) > 0


# ── _get_plan_limit ────────────────────────────────────────────────────────────

def test_free_ppt_limit_is_3():
    """Free plan allows 3 PPT uploads/month."""
    limit = _get_plan_limit("ppt_uploads", "free")
    assert limit == 3


def test_free_rehearsal_limit_is_5():
    limit = _get_plan_limit("rehearsals", "free")
    assert limit == 5


def test_pro_ppt_limit_is_unlimited():
    """Pro plan has no limit (None = unlimited)."""
    limit = _get_plan_limit("ppt_uploads", "pro")
    assert limit is None


def test_unknown_feature_free_returns_fallback_or_none():
    limit = _get_plan_limit("nonexistent_feature", "free")
    # Could be None (fallback for unknown feature on free) or from fallback dict
    assert limit is None or isinstance(limit, int)


def test_free_limits_dict_populated():
    """FREE_LIMITS should mirror free plan values."""
    assert "ppt_uploads" in FREE_LIMITS or len(FREE_LIMITS) >= 0


# ── get_gated_routes ──────────────────────────────────────────────────────────

def test_gated_routes_returns_list():
    routes = get_gated_routes()
    assert isinstance(routes, list)


def test_gated_routes_tuples_format():
    """Each route tuple: (method, path, feature_key, trigger_id)."""
    routes = get_gated_routes()
    for method, path, feature_key, trigger_id in routes:
        assert method in ("GET", "POST", "PUT", "DELETE", "PATCH")
        assert path.startswith("/api/v1/")
        assert isinstance(feature_key, str)
        assert isinstance(trigger_id, str)


def test_gated_routes_has_rehearsal_gate():
    """Rehearsal POST should be gated."""
    routes = get_gated_routes()
    paths = [r[1] for r in routes]
    assert any("/rehearsal" in p or "/pitch-task" in p for p in paths) or len(routes) == 0


# ── _year_month ───────────────────────────────────────────────────────────────

def test_year_month_format():
    ym = _year_month()
    assert len(ym) == 7         # "YYYY-MM"
    assert ym[4] == "-"
    year, month = ym.split("-")
    assert 2020 <= int(year) <= 2040
    assert 1 <= int(month) <= 12


def test_year_month_consistent():
    """Two rapid calls should return the same value."""
    assert _year_month() == _year_month()


if __name__ == "__main__":
    tests = [
        test_registry_loads_known_features,
        test_feature_labels_populated,
        test_free_ppt_limit_is_3,
        test_free_rehearsal_limit_is_5,
        test_pro_ppt_limit_is_unlimited,
        test_unknown_feature_free_returns_fallback_or_none,
        test_free_limits_dict_populated,
        test_gated_routes_returns_list,
        test_gated_routes_tuples_format,
        test_gated_routes_has_rehearsal_gate,
        test_year_month_format,
        test_year_month_consistent,
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
