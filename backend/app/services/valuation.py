from datetime import date
from decimal import Decimal
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Asset, CryptoHolding, FixedIncomeHolding, MutualFundHolding, ValuationHistory
from app.integrations.coingecko import get_crypto_prices
from app.integrations.mfapi import get_latest_nav
from app.services.fixed_income import compound_value


async def _upsert_valuation(
    session: AsyncSession,
    asset_id,
    invested: Decimal,
    current: Decimal,
    pnl: Decimal,
    source: str,
) -> None:
    """Replace today's valuation row for this asset to avoid duplicate accumulation."""
    await session.execute(
        delete(ValuationHistory).where(
            and_(
                ValuationHistory.asset_id == asset_id,
                ValuationHistory.valuation_date == date.today(),
            )
        )
    )
    session.add(ValuationHistory(
        asset_id=asset_id,
        valuation_date=date.today(),
        invested_amount=invested,
        current_value=current,
        pnl=pnl,
        source=source,
    ))


async def recalculate_crypto_valuations(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        select(Asset, CryptoHolding)
        .join(CryptoHolding, CryptoHolding.asset_id == Asset.id)
        .where(Asset.asset_type == "CRYPTO")
    )
    rows = result.all()
    if not rows:
        return []

    coin_ids = [holding.coingecko_id for _, holding in rows]
    prices = await get_crypto_prices(coin_ids)

    output = []
    for asset, holding in rows:
        price = Decimal(str(prices[holding.coingecko_id]["inr"]))
        quantity = Decimal(str(holding.quantity))
        avg_buy_price = Decimal(str(holding.avg_buy_price))

        invested = quantity * avg_buy_price
        current = quantity * price
        pnl = current - invested

        await _upsert_valuation(session, asset.id, invested, current, pnl, "coingecko")

        output.append({
            "asset": asset.name,
            "coin": holding.coingecko_id,
            "price": float(price),
            "quantity": float(quantity),
            "invested_amount": float(invested),
            "current_value": float(current),
            "pnl": float(pnl),
        })

    await session.commit()
    return output


async def recalculate_fixed_income_valuations(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        select(Asset, FixedIncomeHolding)
        .join(FixedIncomeHolding, FixedIncomeHolding.asset_id == Asset.id)
    )
    rows = result.all()
    if not rows:
        return []

    today = date.today()
    output = []
    for asset, holding in rows:
        principal = Decimal(str(holding.principal))
        rate = Decimal(str(holding.annual_rate))
        current = compound_value(principal, rate, holding.start_date, today, holding.compounding_frequency)
        pnl = current - principal

        await _upsert_valuation(session, asset.id, principal, current, pnl, "compound_interest")

        output.append({
            "asset": asset.name,
            "principal": float(principal),
            "current_value": float(current),
            "pnl": float(pnl),
        })

    await session.commit()
    return output


async def recalculate_mf_valuations(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        select(Asset, MutualFundHolding)
        .join(MutualFundHolding, MutualFundHolding.asset_id == Asset.id)
        .where(Asset.asset_type == "MUTUAL_FUND")
    )
    rows = result.all()
    if not rows:
        return []

    output = []
    for asset, holding in rows:
        try:
            nav_data = await get_latest_nav(holding.scheme_code)
            current_nav = Decimal(str(nav_data["nav"]))
        except Exception:
            current_nav = Decimal(str(holding.nav_at_purchase))

        units = Decimal(str(holding.units))
        nav_at_purchase = Decimal(str(holding.nav_at_purchase))

        invested = units * nav_at_purchase
        current = units * current_nav
        pnl = current - invested

        await _upsert_valuation(session, asset.id, invested, current, pnl, "mfapi")

        output.append({
            "asset": asset.name,
            "scheme_code": holding.scheme_code,
            "current_nav": float(current_nav),
            "units": float(units),
            "invested_amount": float(invested),
            "current_value": float(current),
            "pnl": float(pnl),
        })

    await session.commit()
    return output
