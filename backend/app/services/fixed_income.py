from decimal import Decimal
from datetime import date


FREQUENCY = {
    "MONTHLY": 12,
    "QUARTERLY": 4,
    "YEARLY": 1,
}


def compound_value(
    principal: Decimal,
    annual_rate: Decimal,
    start_date: date,
    as_of_date: date,
    frequency: str,
) -> Decimal:
    years = Decimal((as_of_date - start_date).days) / Decimal(365)
    n = Decimal(FREQUENCY[frequency])
    r = annual_rate / Decimal(100)

    amount = principal * ((Decimal(1) + r / n) ** (n * years))
    return amount.quantize(Decimal("0.01"))


def _rd_months_elapsed(start_date: date, as_of: date) -> int:
    months = (as_of.year - start_date.year) * 12 + (as_of.month - start_date.month) + 1
    return max(1, months)


def rd_current_value(
    monthly: Decimal,
    annual_rate: Decimal,
    start_date: date,
    as_of_date: date,
    frequency: str,
) -> Decimal:
    """Current value of a recurring deposit.

    Unlike a lump sum, each monthly installment compounds only from its own deposit
    date to `as_of_date`. Compounding the whole accumulated principal from day 1
    (the old behaviour) overstated the value.
    """
    n = Decimal(FREQUENCY[frequency])
    r = annual_rate / Decimal(100)
    months = _rd_months_elapsed(start_date, as_of_date)

    total = Decimal(0)
    for k in range(months):
        ym = start_date.month - 1 + k
        deposit = date(start_date.year + ym // 12, ym % 12 + 1, min(start_date.day, 28))
        years = Decimal((as_of_date - deposit).days) / Decimal(365)
        total += monthly * ((Decimal(1) + r / n) ** (n * years))
    return total.quantize(Decimal("0.01"))
