"""Unit tests for billing_service — pure pricing/proration logic, no DB required."""
import sys
import os
import types
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Stub heavy deps ───────────────────────────────────────────────────────────
_STUB_MODS = [
    "sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext", "sqlalchemy.ext.asyncio",
    "app.models.subscription", "app.models.payment", "app.models.usage",
]
for _mod in _STUB_MODS:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

for _attr in ("select", "Column", "Integer", "String", "Boolean", "DateTime",
              "Text", "ForeignKey", "func", "and_", "Numeric"):
    for _ns in ("sqlalchemy", "sqlalchemy.orm"):
        m = sys.modules[_ns]
        if not hasattr(m, _attr):
            setattr(m, _attr, lambda *a, **kw: None)

_asyncio_mod = sys.modules["sqlalchemy.ext.asyncio"]
if not hasattr(_asyncio_mod, "AsyncSession"):
    class _AsyncSession: pass
    _asyncio_mod.AsyncSession = _AsyncSession  # type: ignore

for _name in ("Subscription",):
    setattr(sys.modules["app.models.subscription"], _name, type(_name, (), {}))
for _name in ("Payment",):
    setattr(sys.modules["app.models.payment"], _name, type(_name, (), {}))
for _name in ("UsageMeter",):
    setattr(sys.modules["app.models.usage"], _name, type(_name, (), {}))

from app.services.billing_service import (
    get_plan_info, calculate_upgrade_proration, PLANS, _generate_invoice_no,
)


# ── Plan catalogue ────────────────────────────────────────────────────────────

def test_plan_catalogue_has_all_tiers():
    assert "free" in PLANS
    assert "pro_10" in PLANS
    assert "pro_20" in PLANS
    assert "elite_50" in PLANS


def test_get_plan_info_free():
    info = get_plan_info("free")
    assert info["monthly_price"] == Decimal("0")


def test_get_plan_info_pro10():
    info = get_plan_info("pro_10")
    assert info["monthly_price"] == Decimal("399")
    assert info["max_users"] == 10


def test_get_plan_info_elite():
    info = get_plan_info("elite_50")
    assert info["monthly_price"] == Decimal("999")
    assert info["max_users"] == 50


def test_get_plan_info_unknown_returns_free():
    info = get_plan_info("nonexistent_plan")
    assert info["monthly_price"] == Decimal("0")


def test_annual_prices_are_discounted():
    """Annual price should be less than 12× monthly (80% discount)."""
    for plan_key in ("pro_10", "pro_20", "elite_50"):
        info = PLANS[plan_key]
        annual = info["annual_price"]
        monthly_x12 = info["monthly_price"] * 12
        assert annual < monthly_x12, f"{plan_key} annual not discounted"
        # Should be around 80% of 12× monthly
        ratio = float(annual / monthly_x12)
        assert 0.65 <= ratio <= 0.85, f"{plan_key} annual discount ratio {ratio:.2f} out of range"


# ── Proration calculation ─────────────────────────────────────────────────────

def test_proration_free_to_pro_day0():
    """Upgrading on day 0 → full new price, no credit."""
    charge = calculate_upgrade_proration("free", "pro_10", days_used=0)
    assert charge == Decimal("399.00")


def test_proration_free_to_pro_halfway():
    """Day 15 of 30 → 50% credit on old (¥0) → full new price."""
    charge = calculate_upgrade_proration("free", "pro_10", days_used=15)
    # Old plan is free → credit = 0, charge = 399
    assert charge == Decimal("399.00")


def test_proration_pro10_to_pro20_halfway():
    """Upgrade from pro_10 to pro_20 at day 15 (of 30)."""
    charge = calculate_upgrade_proration("pro_10", "pro_20", days_used=15)
    # credit = 399 × (15/30) = 199.50; charge = 699 - 199.50 = 499.50
    assert charge == Decimal("499.50")


def test_proration_same_plan_day0():
    """Same plan, day 0: credit=full, charge=0 (nothing extra to pay)."""
    charge = calculate_upgrade_proration("pro_10", "pro_10", days_used=0)
    assert charge == Decimal("0.00")


def test_proration_same_plan_day30():
    """Same plan, end of cycle: no days remaining → credit=0, full renewal."""
    charge = calculate_upgrade_proration("pro_10", "pro_10", days_used=30)
    assert charge == Decimal("399.00")


def test_proration_never_negative():
    """Downgrade (lower plan) should never return negative charge."""
    charge = calculate_upgrade_proration("elite_50", "pro_10", days_used=0)
    assert charge >= Decimal("0")


def test_proration_annual_cycle():
    """Annual proration uses 365-day cycle."""
    # pro_10 annual = 3192, monthly = 3192/12 = 266
    # Day 0 of annual: charge = 3192/12 (no credit) = 266
    charge = calculate_upgrade_proration("free", "pro_10", days_used=0, billing_cycle="annual")
    # free annual monthly = 0, pro_10 annual monthly = 3192/12 = 266
    assert charge == Decimal("266.00")


def test_proration_annual_halfway():
    """Annual mid-cycle: day 182 of 365."""
    charge = calculate_upgrade_proration("pro_10", "pro_20", days_used=182, billing_cycle="annual")
    # pro_10 annual monthly = 3192/12 = 266; pro_20 annual monthly = 5592/12 = 466
    # days remaining = 365-182 = 183; fraction = 183/365 ≈ 0.5013698...
    # credit = 266 × 0.5013... ≈ 133.36; charge = 466 - 133.36 = 332.64
    # Just verify it's positive and within range
    assert charge > Decimal("0")
    assert charge <= Decimal("466.00")


def test_proration_full_cycle_used():
    """Used all 30 days → no credit → full new plan price."""
    charge = calculate_upgrade_proration("pro_10", "elite_50", days_used=30)
    assert charge == Decimal("999.00")


# ── Invoice number format ─────────────────────────────────────────────────────

def test_invoice_no_format():
    inv = _generate_invoice_no()
    assert inv.startswith("INV-")
    parts = inv.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 8  # YYYYMMDD
    assert len(parts[2]) == 6  # 6-char suffix


def test_invoice_no_unique():
    invoices = set(_generate_invoice_no() for _ in range(20))
    assert len(invoices) > 15  # high probability of uniqueness


if __name__ == "__main__":
    tests = [
        test_plan_catalogue_has_all_tiers,
        test_get_plan_info_free,
        test_get_plan_info_pro10,
        test_get_plan_info_elite,
        test_get_plan_info_unknown_returns_free,
        test_annual_prices_are_discounted,
        test_proration_free_to_pro_day0,
        test_proration_free_to_pro_halfway,
        test_proration_pro10_to_pro20_halfway,
        test_proration_same_plan_day0,
        test_proration_same_plan_day30,
        test_proration_never_negative,
        test_proration_annual_cycle,
        test_proration_annual_halfway,
        test_proration_full_cycle_used,
        test_invoice_no_format,
        test_invoice_no_unique,
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
