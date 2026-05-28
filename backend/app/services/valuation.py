from datetime import date
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Asset, CryptoHolding, ValuationHistory
from app.integrations.coingecko import get_crypto_prices


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
        quantity = Decimal(holding.quantity)
        avg_buy_price = Decimal(holding.avg_buy_price)

        invested_amount = quantity * avg_buy_price
        current_value = quantity * price
        pnl = current_value - invested_amount

        valuation = ValuationHistory(
            asset_id=asset.id,
            valuation_date=date.today(),
            invested_amount=invested_amount,
            current_value=current_value,
            pnl=pnl,
            source="coingecko",
        )

        session.add(valuation)

        output.append({
            "asset": asset.name,
            "coin": holding.coingecko_id,
            "price": float(price),
            "quantity": float(quantity),
            "invested_amount": float(invested_amount),
            "current_value": float(current_value),
            "pnl": float(pnl),
        })

    await session.commit()
    return output
