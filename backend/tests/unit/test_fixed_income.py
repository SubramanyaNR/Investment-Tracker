"""Unit tests for the compound-interest engine (FD / PPF / RD principal growth)."""
from datetime import date
from decimal import Decimal

import pytest

from app.services.fixed_income import FREQUENCY, compound_value

pytestmark = pytest.mark.unit
D = Decimal


def test_yearly_one_year_exact():
    # 2024-01-01 -> 2024-12-31 is exactly 365 days => years = 1; 10% yearly => +10%.
    assert compound_value(D("100000"), D("10"), date(2024, 1, 1), date(2024, 12, 31), "YEARLY") == D("110000.00")


def test_zero_elapsed_returns_principal():
    d = date(2024, 1, 1)
    assert compound_value(D("100000"), D("10"), d, d, "YEARLY") == D("100000.00")


def test_result_quantized_to_paise():
    v = compound_value(D("100000"), D("7.35"), date(2024, 1, 1), date(2025, 1, 1), "QUARTERLY")
    assert v.as_tuple().exponent == -2  # always two decimal places


def test_higher_frequency_yields_more():
    args = (D("100000"), D("10"), date(2024, 1, 1), date(2024, 12, 31))
    yearly = compound_value(*args, "YEARLY")
    quarterly = compound_value(*args, "QUARTERLY")
    monthly = compound_value(*args, "MONTHLY")
    assert monthly > quarterly > yearly


def test_uses_365_day_year_not_calendar_year():
    # A leap-year window is 366 days, so years > 1 and the result exceeds a clean +10%.
    leap = compound_value(D("100000"), D("10"), date(2024, 1, 1), date(2025, 1, 1), "YEARLY")
    assert leap > D("110000.00")


def test_unknown_frequency_raises_keyerror():
    # Documents current behaviour: frequency is not validated before lookup.
    with pytest.raises(KeyError):
        compound_value(D("100000"), D("10"), date(2024, 1, 1), date(2025, 1, 1), "WEEKLY")


def test_frequency_map_values():
    assert FREQUENCY == {"MONTHLY": 12, "QUARTERLY": 4, "YEARLY": 1}
