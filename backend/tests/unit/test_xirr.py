"""Unit tests for the XIRR Newton-Raphson solver — F5.

Financial calculations must be correct before touching real data.
All tests validate the pure algorithm (_newton_raphson + _build_cash_flows),
not the DB-dependent compute_xirr function (covered in integration tests).
"""
import pytest
from datetime import date
from app.services.xirr import _newton_raphson, _build_cash_flows

pytestmark = pytest.mark.unit

# ── Helper ─────────────────────────────────────────────────────────────────

def flows(*pairs) -> list[tuple[date, float]]:
    """Build cash flow list from alternating (date_str, amount) pairs."""
    result = []
    it = iter(pairs)
    for d, a in zip(it, it):
        result.append((date.fromisoformat(d), float(a)))
    return result


# ── U1: Classic lump-sum — known XIRR ─────────────────────────────────────

def test_lump_sum_10pct():
    """U1 — invest ₹100k, worth ₹110k exactly one year later → ~10% XIRR."""
    cf = flows("2022-01-01", -100_000, "2023-01-01", 110_000)
    r = _newton_raphson(cf)
    assert r is not None
    assert abs(r - 0.10) < 0.001


def test_lump_sum_negative_return():
    """Invest ₹100k, worth ₹80k one year later → negative XIRR."""
    cf = flows("2022-01-01", -100_000, "2023-01-01", 80_000)
    r = _newton_raphson(cf)
    assert r is not None
    assert r < 0


def test_lump_sum_6_months():
    """Invest ₹100k, worth ₹105k after 6 months → ~10% annualised."""
    cf = flows("2022-01-01", -100_000, "2022-07-01", 105_000)
    r = _newton_raphson(cf)
    assert r is not None
    assert 0.09 < r < 0.12


# ── U2: Monthly SIP ────────────────────────────────────────────────────────

def test_monthly_sip_positive_xirr():
    """U2 — 12 × ₹5000 monthly SIP, current value ₹70000 → positive XIRR."""
    cf = []
    for month in range(12):
        d = date(2022, month + 1, 1)
        cf.append((d, -5_000.0))
    cf.append((date(2023, 1, 1), 70_000.0))
    r = _newton_raphson(cf)
    assert r is not None
    assert r > 0.10   # decent return on SIP


# ── U3–U6: Edge cases — None returns ──────────────────────────────────────

def test_empty_returns_none():
    """U3 — empty cash flows → None."""
    assert _newton_raphson([]) is None


def test_single_flow_returns_none():
    """U3b — single cash flow → None (need at least 2 data points)."""
    assert _newton_raphson(flows("2022-01-01", -100_000)) is None


def test_all_outflows_returns_none():
    """U4 — all outflows, no inflow → None."""
    cf = flows("2022-01-01", -100_000, "2022-06-01", -50_000)
    assert _newton_raphson(cf) is None


def test_all_inflows_returns_none():
    """U4b — all inflows, no outflow → None."""
    cf = flows("2022-01-01", 100_000, "2022-06-01", 50_000)
    assert _newton_raphson(cf) is None


def test_identical_dates_handled_gracefully():
    """U5 — same buy and sell date: may return value or None, must not raise."""
    cf = flows("2022-01-01", -100_000, "2022-01-01", 105_000)
    result = _newton_raphson(cf)  # either a value or None — not an exception
    assert result is None or isinstance(result, float)


def test_total_loss_returns_none_or_negative():
    """U6 — invest ₹100k, current value ₹0 → returns None (terminal 0 = all outflows)."""
    cf = _build_cash_flows(
        [("BUY", date(2022, 1, 1), 100_000)],
        current_value=0,
        today=date(2023, 1, 1),
    )
    r = _newton_raphson(cf)
    # No inflow → no valid XIRR
    assert r is None


# ── U7: Partial sell ───────────────────────────────────────────────────────

def test_partial_sell_then_remaining():
    """U7 — buy ₹100k, sell half at ₹60k, remaining worth ₹60k → positive XIRR."""
    cf = flows(
        "2021-01-01", -100_000,
        "2022-01-01",  60_000,   # partial sell
        "2023-01-01",  60_000,   # remaining value today
    )
    r = _newton_raphson(cf)
    assert r is not None
    assert r > 0.10


# ── U8: Long holding period ────────────────────────────────────────────────

def test_10_year_holding():
    """U8 — invest ₹100k in 2014, worth ₹400k in 2024 → ~15% XIRR."""
    cf = flows("2014-01-01", -100_000, "2024-01-01", 400_000)
    r = _newton_raphson(cf)
    assert r is not None
    assert 0.14 < r < 0.17   # ~14.87% for 4x in 10 years


# ── U9: build_cash_flows helper ────────────────────────────────────────────

def test_build_cash_flows_signs():
    """U9 — BUY is negative, DEPOSIT is negative, SELL is positive, current value is positive."""
    txs = [
        ("BUY",     date(2022, 1, 1), 50_000),
        ("DEPOSIT", date(2022, 3, 1), 10_000),
        ("SELL",    date(2022, 6, 1), 20_000),
    ]
    cf = _build_cash_flows(txs, current_value=45_000, today=date(2023, 1, 1))

    assert cf[0] == (date(2022, 1, 1), -50_000)
    assert cf[1] == (date(2022, 3, 1), -10_000)
    assert cf[2] == (date(2022, 6, 1),  20_000)
    assert cf[3] == (date(2023, 1, 1),  45_000)


def test_build_cash_flows_zero_current_value():
    """Terminal flow is omitted when current_value = 0."""
    txs = [("BUY", date(2022, 1, 1), 50_000)]
    cf = _build_cash_flows(txs, current_value=0, today=date(2023, 1, 1))
    assert len(cf) == 1
    assert cf[0][1] == -50_000


# ── U10: XIRR precision ────────────────────────────────────────────────────

def test_xirr_result_precision():
    """XIRR is rounded to 6 decimal places."""
    cf = flows("2022-01-01", -100_000, "2023-01-01", 115_000)
    r = _newton_raphson(cf)
    assert r is not None
    # Should have at most 6 decimal places
    assert r == round(r, 6)
