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
