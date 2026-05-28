from decimal import Decimal
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from typing import Optional
from app.db.session import AsyncSessionLocal
from app.db.models import Asset, CryptoHolding, FixedIncomeHolding, Transaction

router = APIRouter()

FI_TYPES = {"FD", "RD", "PPF"}


class AssetCreate(BaseModel):
    name: str
    asset_type: str
    category: str
    liquidity_tier: str
    # Crypto
    coingecko_id: Optional[str] = None
    symbol: Optional[str] = None
    quantity: Optional[Decimal] = None
    avg_buy_price: Optional[Decimal] = None
    # Fixed income
    principal: Optional[Decimal] = None
    annual_rate: Optional[Decimal] = None
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    compounding_frequency: Optional[str] = None


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


def _asset_row(asset: Asset) -> dict:
    return {
        "id": str(asset.id),
        "name": asset.name,
        "asset_type": asset.asset_type,
        "category": asset.category,
        "liquidity_tier": asset.liquidity_tier,
        "created_at": str(asset.created_at),
    }


@router.get("/assets")
async def list_assets(session=Depends(get_session)):
    result = await session.execute(select(Asset).order_by(Asset.created_at.desc()))
    assets = result.scalars().all()

    if not assets:
        return []

    asset_ids = [a.id for a in assets]

    crypto_result = await session.execute(
        select(CryptoHolding).where(CryptoHolding.asset_id.in_(asset_ids))
    )
    crypto_map = {str(h.asset_id): h for h in crypto_result.scalars().all()}

    fi_result = await session.execute(
        select(FixedIncomeHolding).where(FixedIncomeHolding.asset_id.in_(asset_ids))
    )
    fi_map = {str(h.asset_id): h for h in fi_result.scalars().all()}

    rows = []
    for asset in assets:
        aid = str(asset.id)
        row: dict = _asset_row(asset)

        if asset.asset_type == "CRYPTO" and aid in crypto_map:
            h = crypto_map[aid]
            row["holding"] = {
                "symbol": h.symbol,
                "coingecko_id": h.coingecko_id,
                "quantity": float(h.quantity),
                "avg_buy_price": float(h.avg_buy_price),
            }
        elif asset.asset_type in FI_TYPES and aid in fi_map:
            fi = fi_map[aid]
            row["fi_holding"] = {
                "principal": float(fi.principal),
                "annual_rate": float(fi.annual_rate),
                "start_date": str(fi.start_date),
                "maturity_date": str(fi.maturity_date) if fi.maturity_date else None,
                "compounding_frequency": fi.compounding_frequency,
            }

        rows.append(row)

    return rows


@router.post("/assets")
async def create_asset(payload: AssetCreate, session=Depends(get_session)):

    # ── CRYPTO ──────────────────────────────────────────────────────────────
    if payload.asset_type == "CRYPTO":
        if not payload.coingecko_id or not payload.symbol:
            raise HTTPException(status_code=400, detail="Crypto requires coingecko_id and symbol")

        add_qty = payload.quantity or Decimal("0")
        add_price = payload.avg_buy_price or Decimal("0")

        existing_result = await session.execute(
            select(CryptoHolding).where(CryptoHolding.coingecko_id == payload.coingecko_id)
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            old_qty = existing.quantity
            old_avg = existing.avg_buy_price
            total_qty = old_qty + add_qty
            if total_qty > 0:
                existing.avg_buy_price = (old_qty * old_avg + add_qty * add_price) / total_qty
            existing.quantity = total_qty

            session.add(Transaction(
                asset_id=existing.asset_id,
                transaction_type="BUY",
                transaction_date=date.today(),
                amount=add_qty * add_price,
                units=add_qty,
                price_per_unit=add_price,
            ))
            await session.commit()

            asset_result = await session.execute(
                select(Asset).where(Asset.id == existing.asset_id)
            )
            asset = asset_result.scalar_one()
        else:
            asset = Asset(
                name=payload.name,
                asset_type=payload.asset_type,
                category=payload.category,
                liquidity_tier=payload.liquidity_tier,
            )
            session.add(asset)
            await session.flush()

            session.add(CryptoHolding(
                asset_id=asset.id,
                coingecko_id=payload.coingecko_id,
                symbol=payload.symbol,
                quantity=add_qty,
                avg_buy_price=add_price,
            ))
            session.add(Transaction(
                asset_id=asset.id,
                transaction_type="BUY",
                transaction_date=date.today(),
                amount=add_qty * add_price,
                units=add_qty,
                price_per_unit=add_price,
            ))
            await session.commit()
            await session.refresh(asset)

        return _asset_row(asset)

    # ── FIXED INCOME (FD / RD / PPF) ────────────────────────────────────────
    if payload.asset_type in FI_TYPES:
        if payload.principal is None or payload.annual_rate is None or payload.start_date is None:
            raise HTTPException(
                status_code=400,
                detail=f"{payload.asset_type} requires principal, annual_rate, and start_date",
            )

        asset = Asset(
            name=payload.name,
            asset_type=payload.asset_type,
            category=payload.category,
            liquidity_tier=payload.liquidity_tier,
        )
        session.add(asset)
        await session.flush()

        session.add(FixedIncomeHolding(
            asset_id=asset.id,
            principal=payload.principal,
            annual_rate=payload.annual_rate,
            start_date=payload.start_date,
            maturity_date=payload.maturity_date,
            compounding_frequency=payload.compounding_frequency or "YEARLY",
        ))
        session.add(Transaction(
            asset_id=asset.id,
            transaction_type="DEPOSIT",
            transaction_date=payload.start_date,
            amount=payload.principal,
            units=None,
            price_per_unit=None,
        ))
        await session.commit()
        await session.refresh(asset)
        return _asset_row(asset)

    # ── MUTUAL FUND + other ─────────────────────────────────────────────────
    asset = Asset(
        name=payload.name,
        asset_type=payload.asset_type,
        category=payload.category,
        liquidity_tier=payload.liquidity_tier,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return _asset_row(asset)


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
async def sell_crypto(asset_id: str, payload: CryptoSellRequest, session=Depends(get_session)):
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

    session.add(Transaction(
        asset_id=holding.asset_id,
        transaction_type="SELL",
        transaction_date=date.today(),
        amount=payload.quantity * holding.avg_buy_price,
        units=payload.quantity,
        price_per_unit=holding.avg_buy_price,
    ))
    await session.commit()

    return {"asset_id": asset_id, "remaining_quantity": float(holding.quantity)}
