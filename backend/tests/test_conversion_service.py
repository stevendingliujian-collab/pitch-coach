"""Unit tests for conversion_service — trigger registry and pure-logic checks."""
import sys
import os
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Stub heavy deps ───────────────────────────────────────────────────────────
_STUB_MODS = [
    "sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext", "sqlalchemy.ext.asyncio",
    "sqlalchemy.dialects", "sqlalchemy.dialects.postgresql",
    "app.models.conversion", "app.models.user",
]
for _mod in _STUB_MODS:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

for _attr in ("select", "func", "and_", "Column", "Integer", "String",
              "Boolean", "DateTime", "Text", "ForeignKey", "Index", "update"):
    for _ns in ("sqlalchemy", "sqlalchemy.orm"):
        m = sys.modules[_ns]
        if not hasattr(m, _attr):
            setattr(m, _attr, lambda *a, **kw: None)

_pg_mod = sys.modules["sqlalchemy.dialects.postgresql"]
if not hasattr(_pg_mod, "insert"):
    _pg_mod.insert = lambda *a, **kw: None  # type: ignore

_asyncio_mod = sys.modules["sqlalchemy.ext.asyncio"]
if not hasattr(_asyncio_mod, "AsyncSession"):
    class _AS: pass
    _asyncio_mod.AsyncSession = _AS  # type: ignore

for _name in ("UpgradeTrigger", "TriggerEvent", "AnalyticsEvent"):
    setattr(sys.modules["app.models.conversion"], _name, type(_name, (), {}))
for _name in ("User",):
    setattr(sys.modules["app.models.user"], _name, type(_name, (), {}))

from app.services.conversion_service import TRIGGERS


# ── Trigger registry ──────────────────────────────────────────────────────────

def test_all_nine_triggers_defined():
    for tid in ("T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9"):
        assert tid in TRIGGERS, f"Missing trigger {tid}"


def test_trigger_required_fields():
    required = {"label", "message", "target", "max_shows", "cooldown_days"}
    for tid, config in TRIGGERS.items():
        missing = required - config.keys()
        assert not missing, f"Trigger {tid} missing fields: {missing}"


def test_trigger_max_shows_is_one():
    """All triggers should fire at most once per user."""
    for tid, config in TRIGGERS.items():
        assert config["max_shows"] == 1, f"{tid} max_shows should be 1"


def test_trigger_cooldown_positive():
    for tid, config in TRIGGERS.items():
        assert config["cooldown_days"] > 0, f"{tid} cooldown must be > 0"


def test_t9_has_shorter_cooldown():
    """T9 (deadline urgency) should have ≤7 day cooldown for repeated urgency."""
    assert TRIGGERS["T9"]["cooldown_days"] <= 7


def test_free_to_pro_triggers():
    """T1-T6 and T9 target free→pro upgrade."""
    for tid in ("T1", "T2", "T3", "T4", "T5", "T6", "T9"):
        target = TRIGGERS[tid]["target"]
        assert "free" in target and "pro" in target, f"{tid} target: {target}"


def test_pro_to_premium_triggers():
    """T7, T8 target pro→premium upgrade."""
    for tid in ("T7", "T8"):
        target = TRIGGERS[tid]["target"]
        assert "pro" in target


def test_trigger_messages_not_empty():
    for tid, config in TRIGGERS.items():
        msg = config["message"]
        assert isinstance(msg, str) and len(msg) > 10, f"{tid} message too short"


def test_trigger_labels_not_empty():
    for tid, config in TRIGGERS.items():
        label = config["label"]
        assert isinstance(label, str) and len(label) > 0, f"{tid} label empty"


if __name__ == "__main__":
    tests = [
        test_all_nine_triggers_defined,
        test_trigger_required_fields,
        test_trigger_max_shows_is_one,
        test_trigger_cooldown_positive,
        test_t9_has_shorter_cooldown,
        test_free_to_pro_triggers,
        test_pro_to_premium_triggers,
        test_trigger_messages_not_empty,
        test_trigger_labels_not_empty,
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
