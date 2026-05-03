"""Unit tests for ab_test_service — deterministic bucketing logic."""
import sys
import os
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub heavy deps so pure-logic functions can be imported without a full stack
_STUB_MODS = [
    "sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext", "sqlalchemy.ext.asyncio",
    "pydantic", "pydantic.v1",
    "app.core.database", "app.models.ab_test",
    "app.core.security", "app.models.user",
]
for _mod in _STUB_MODS:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

# Populate common sqlalchemy symbols
for _attr in ("select", "Column", "Integer", "String", "Boolean", "DateTime",
              "Text", "SmallInteger", "ForeignKey", "Index", "UniqueConstraint",
              "func", "and_", "or_", "insert", "update", "delete"):
    for _ns in ("sqlalchemy", "sqlalchemy.orm"):
        mod = sys.modules[_ns]
        if not hasattr(mod, _attr):
            setattr(mod, _attr, lambda *a, **kw: None)

# AsyncSession stub
_asyncio_mod = sys.modules["sqlalchemy.ext.asyncio"]
if not hasattr(_asyncio_mod, "AsyncSession"):
    class _AsyncSession: pass  # type: ignore
    _asyncio_mod.AsyncSession = _AsyncSession  # type: ignore

# Model stubs
class _ModelStub:
    def __init__(self, *a, **kw): pass
_ab_test_mod = sys.modules["app.models.ab_test"]
_ab_test_mod.AbTest = _ModelStub  # type: ignore
_ab_test_mod.AbTestAssignment = _ModelStub  # type: ignore
_ab_test_mod.AbTestEvent = _ModelStub  # type: ignore

from app.services.ab_test_service import _bucket, _pick_variant  # noqa: E402


def test_bucket_deterministic():
    """Same user + test always returns same bucket."""
    b1 = _bucket(42, "pricing_layout")
    b2 = _bucket(42, "pricing_layout")
    assert b1 == b2


def test_bucket_in_range():
    """Bucket is always 0-99."""
    for user_id in [1, 100, 9999, 12345678]:
        b = _bucket(user_id, "test_a")
        assert 0 <= b < 100


def test_bucket_differs_by_user():
    """Different users should (mostly) get different buckets."""
    buckets = set(_bucket(i, "pricing_layout") for i in range(1, 101))
    assert len(buckets) > 50  # reasonable spread


def test_bucket_differs_by_test():
    """Same user, different test names → probably different buckets."""
    b1 = _bucket(1, "test_x")
    b2 = _bucket(1, "test_y")
    # Not always different but should not always be equal
    buckets = set(_bucket(1, f"test_{i}") for i in range(20))
    assert len(buckets) > 1


def test_pick_variant_equal_split():
    """50/50 split: bucket 0-49 → control, 50-99 → variant_b."""
    variants = ["control", "variant_b"]
    weights = [50, 50]
    assert _pick_variant(0, variants, weights) == "control"
    assert _pick_variant(49, variants, weights) == "control"
    assert _pick_variant(50, variants, weights) == "variant_b"
    assert _pick_variant(99, variants, weights) == "variant_b"


def test_pick_variant_unequal_split():
    variants = ["control", "variant_b"]
    weights = [70, 30]
    assert _pick_variant(0, variants, weights) == "control"
    assert _pick_variant(69, variants, weights) == "control"
    assert _pick_variant(70, variants, weights) == "variant_b"
    assert _pick_variant(99, variants, weights) == "variant_b"


def test_pick_variant_three_way():
    variants = ["a", "b", "c"]
    weights = [33, 33, 34]
    assert _pick_variant(0, variants, weights) == "a"
    assert _pick_variant(32, variants, weights) == "a"
    assert _pick_variant(33, variants, weights) == "b"
    assert _pick_variant(65, variants, weights) == "b"
    assert _pick_variant(66, variants, weights) == "c"
    assert _pick_variant(99, variants, weights) == "c"


def test_pick_variant_fallback_equal():
    """No weights provided → equal split."""
    variants = ["a", "b"]
    result = _pick_variant(0, variants, None)
    assert result in variants


def test_pick_variant_empty():
    """Empty variant list → returns 'control' fallback."""
    assert _pick_variant(50, [], None) == "control"


if __name__ == "__main__":
    tests = [
        test_bucket_deterministic,
        test_bucket_in_range,
        test_bucket_differs_by_user,
        test_bucket_differs_by_test,
        test_pick_variant_equal_split,
        test_pick_variant_unequal_split,
        test_pick_variant_three_way,
        test_pick_variant_fallback_equal,
        test_pick_variant_empty,
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
