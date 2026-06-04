"""Unit tests for recurring-deposit (RD) valuation.

Covers the month-elapsed helper and locks in the A4 correctness gap: the current
production path compounds the *entire accumulated principal from day 1*, which
overstates an RD versus compounding each installment from its own deposit date.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.services.fixed_income import FREQUENCY, compound_value
from app.services.valuation import _rd_months_elapsed

pytestmark = pytest.mark.unit
D = Decimal


# ── _rd_months_elapsed ───────────────────────────────────────────────────────

def test_same_month_is_one():
    assert _rd_months_elapsed(date(2025, 1, 10), date(2025, 1, 20)) == 1


def test_one_month_later_is_two():
    assert _rd_months_elapsed(date(2025, 1, 1), date(2025, 2, 1)) == 2


def test_full_year_is_thirteen():
    # The +1 means the start month counts as month 1.
    assert _rd_months_elapsed(date(2025, 1, 1), date(2026, 1, 1)) == 13


def test_as_of_before_start_floors_to_one():
    assert _rd_months_elapsed(date(2025, 6, 1), date(2025, 1, 1)) == 1


# ── RD valuation correctness (A4) ────────────────────────────────────────────

def _rd_reference(monthly, annual_rate, start, as_of, frequency):
    """Intended-correct RD value: each monthly installment compounds only from its
    own deposit date to `as_of`. This is the target behaviour for A4."""
    n = D(FREQUENCY[frequency])
    r = D(str(annual_rate)) / D(100)
    months = _rd_months_elapsed(start, as_of)
    total = D(0)
    for k in range(months):
        ym = start.month - 1 + k
        deposit = date(start.year + ym // 12, ym % 12 + 1, min(start.day, 28))
        years = D((as_of - deposit).days) / D(365)
        total += D(str(monthly)) * ((D(1) + r / n) ** (n * years))
    return total.quantize(D("0.01"))


def test_current_inline_formula_overstates_rd_value():
    """Lock the A4 bug: the production approach is optimistic vs per-installment."""
    monthly, rate, freq = D("10000"), D("7"), "QUARTERLY"
    start, as_of = date(2024, 1, 1), date(2025, 1, 1)
    invested = monthly * _rd_months_elapsed(start, as_of)
    current_inline = compound_value(invested, rate, start, as_of, freq)  # production behaviour today
    reference = _rd_reference(monthly, rate, start, as_of, freq)
    assert current_inline > reference


def test_rd_current_value_matches_per_installment_reference():
    """A4: each installment compounds from its own deposit date (per-installment)."""
    from app.services.fixed_income import rd_current_value

    monthly, rate, freq = D("10000"), D("7"), "QUARTERLY"
    start, as_of = date(2024, 1, 1), date(2025, 1, 1)
    assert rd_current_value(monthly, rate, start, as_of, freq) == _rd_reference(monthly, rate, start, as_of, freq)
