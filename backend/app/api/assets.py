from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Asset, CryptoHolding
from fastapi import APIRouter, Depends, HTTPException
from app.db.models import Asset, CryptoHolding

router = APIRouter()


class AssetCreate(BaseModel):
    name: str
    asset_type: str
    category: str
    liquidity_tier: str
    coingecko_id: str | None = None
    symbol: str | None = None
    quantity: Decimal | None = None
    avg_buy_price: Decimal | None = None


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/assets")
async def list_assets(session=Depends(get_session)):
    result = await session.execute(select(Asset).order_by(Asset.created_at.desc()))
    assets = result.scalars().all()

    if not assets:
        return []

    asset_ids = [a.id for a in assets]
    holdings_result = await session.execute(
        select(CryptoHolding).where(CryptoHolding.asset_id.in_(asset_ids))
    )
    holdings_map = {str(h.asset_id): h for h in holdings_result.scalars().all()}

    rows = []
    for asset in assets:
        row: dict = {
            "id": str(asset.id),
            "name": asset.name,
            "asset_type": asset.asset_type,
            "category": asset.category,
            "liquidity_tier": asset.liquidity_tier,
            "created_at": str(asset.created_at),
        }
        if asset.asset_type == "CRYPTO":
            h = holdings_map.get(str(asset.id))
            if h:
                row["holding"] = {
                    "symbol": h.symbol,
                    "coingecko_id": h.coingecko_id,
                    "quantity": float(h.quantity),
                    "avg_buy_price": float(h.avg_buy_price),
                }
        rows.append(row)

    return rows


@router.post("/assets")
async def create_asset(payload: AssetCreate, session=Depends(get_session)):
    asset = Asset(
        name=payload.name,
        asset_type=payload.asset_type,
        category=payload.category,
        liquidity_tier=payload.liquidity_tier,
    )
    session.add(asset)
    await session.flush()

    if payload.asset_type == "CRYPTO":
        if not payload.coingecko_id or not payload.symbol:
            raise ValueError("Crypto assets require coingecko_id and symbol")

        holding = CryptoHolding(
            asset_id=asset.id,
            coingecko_id=payload.coingecko_id,
            symbol=payload.symbol,
            quantity=payload.quantity or Decimal("0"),
            avg_buy_price=payload.avg_buy_price or Decimal("0"),
        )
        session.add(holding)

    await session.commit()
    await session.refresh(asset)

    return {
        "id": str(asset.id),
        "name": asset.name,
        "asset_type": asset.asset_type,
        "category": asset.category,
        "liquidity_tier": asset.liquidity_tier,
        "created_at": str(asset.created_at),
    }

@router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: str, session=Depends(get_session)):
    result = await session.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    await session.delete(asset)
    await session.commit()

    return {"deleted": True, "asset_id": asset_id}


class CryptoSellRequest(BaseModel):
    quantity: Decimal


@router.post("/assets/{asset_id}/sell-crypto")
async def sell_crypto(
    asset_id: str,
    payload: CryptoSellRequest,
    session=Depends(get_session),
):
    result = await session.execute(
        select(CryptoHolding).where(CryptoHolding.asset_id == asset_id)
    )
    holding = result.scalar_one_or_none()

    if not holding:
        raise HTTPException(status_code=404, detail="Crypto holding not found")

    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Sell quantity must be positive")

    if payload.quantity > holding.quantity:
        raise HTTPException(status_code=400, detail="Cannot sell more than current quantity")

    holding.quantity = holding.quantity - payload.quantity

    await session.commit()

    return {
        "asset_id": asset_id,
        "remaining_quantity": float(holding.quantity),
    }
