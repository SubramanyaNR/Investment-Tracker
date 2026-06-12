import uuid
from decimal import Decimal
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, delete, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from typing import Optional
from app.api.deps import get_session
from app.db.models import Asset, CryptoHolding, FixedIncomeHolding, ManualHolding, MutualFundHolding, Transaction, ValuationHistory, User


async def _complete_onboarding(session, user_id: uuid.UUID) -> None:
    """Mark onboarding as completed for the user — idempotent upsert."""
    stmt = (
        pg_insert(User)
        .values(id=user_id, onboarding_completed=True)
        .on_conflict_do_update(
            index_elements=["id"],
            set_=dict(onboarding_completed=True)
        )
    )
    await session.execute(stmt)
from app.services.fixed_income import compound_value, rd_current_value
from app.core.auth import get_current_user_id

router = APIRouter()

FI_TYPES = {"FD", "RD", "PPF", "SAVINGS_ACC"}


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
    # Mutual fund
    scheme_code: Optional[str] = None
    amount_invested: Optional[Decimal] = None   # total corpus user enters
    nav_at_purchase: Optional[Decimal] = None
    monthly_sip: Optional[Decimal] = None
    # Manual
    cost_basis: Optional[Decimal] = None        # what the user paid
    current_value: Optional[Decimal] = None     # user's current estimate
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("quantity", "avg_buy_price", "principal", "amount_invested", "nav_at_purchase", "monthly_sip", "cost_basis", "current_value")
    @classmethod
    def _positive_amounts(cls, v, info):
        if v is not None and v <= 0:
            raise ValueError(f"{info.field_name} must be greater than zero")
        return v

    @field_validator("annual_rate")
    @classmethod
    def _non_negative_rate(cls, v):
        if v is not None and v < 0:
            raise ValueError("annual_rate must not be negative")
        return v


def _asset_row(asset: Asset) -> dict:
    return {
        "id": str(asset.id),
        "name": asset.name,
        "asset_type": asset.asset_type,
        "category": asset.category,
        "liquidity_tier": asset.liquidity_tier,
        "created_at": str(asset.created_at),
    }


def _rd_months_elapsed(start_date: date, as_of: date) -> int:
    months = (as_of.year - start_date.year) * 12 + (as_of.month - start_date.month) + 1
    return max(1, months)


async def _write_initial_valuation(
    session,
    user_id: uuid.UUID,
    asset_id,
    invested: Decimal,
    current: Decimal,
    pnl: Decimal,
    source: str = "initial",
) -> None:
    """Delete-then-insert for today so duplicates can never accumulate."""
    await session.execute(
        delete(ValuationHistory).where(
            and_(
                ValuationHistory.user_id == user_id,
                ValuationHistory.asset_id == asset_id,
                ValuationHistory.valuation_date == date.today(),
            )
        )
    )
    session.add(ValuationHistory(
        user_id=user_id,
        asset_id=asset_id,
        valuation_date=date.today(),
        invested_amount=invested,
        current_value=current,
        pnl=pnl,
        source=source,
    ))


@router.get("/assets")
async def list_assets(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    result = await session.execute(
        select(Asset).where(Asset.user_id == user_id).order_by(Asset.created_at.desc())
    )
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

    mf_result = await session.execute(
        select(MutualFundHolding).where(MutualFundHolding.asset_id.in_(asset_ids))
    )
    mf_map = {str(h.asset_id): h for h in mf_result.scalars().all()}

    manual_result = await session.execute(
        select(ManualHolding).where(ManualHolding.asset_id.in_(asset_ids))
    )
    manual_map = {str(h.asset_id): h for h in manual_result.scalars().all()}

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
        elif asset.asset_type == "MUTUAL_FUND" and aid in mf_map:
            mf = mf_map[aid]
            row["mf_holding"] = {
                "scheme_code": mf.scheme_code,
                "units": float(mf.units),
                "nav_at_purchase": float(mf.nav_at_purchase),
                "monthly_sip": float(mf.monthly_sip) if mf.monthly_sip else None,
                "amount_invested": float(mf.units * mf.nav_at_purchase),
            }
        elif asset.asset_type == "MANUAL" and aid in manual_map:
            m = manual_map[aid]
            row["manual_holding"] = {
                "cost_basis": float(m.cost_basis),
                "current_value": float(m.current_value),
                "notes": m.notes,
                "value_updated_at": m.value_updated_at.isoformat(),
            }

        rows.append(row)

    return rows


@router.post("/assets")
async def create_asset(
    payload: AssetCreate,
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):

    # ── CRYPTO ──────────────────────────────────────────────────────────────
    if payload.asset_type == "CRYPTO":
        if not payload.coingecko_id or not payload.symbol:
            raise HTTPException(status_code=400, detail="Crypto requires coingecko_id and symbol")

        add_qty = payload.quantity or Decimal("0")
        add_price = payload.avg_buy_price or Decimal("0")

        existing_result = await session.execute(
            select(CryptoHolding).where(
                and_(
                    CryptoHolding.coingecko_id == payload.coingecko_id,
                    CryptoHolding.user_id == user_id,
                )
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is None:
            try:
                asset = Asset(
                    user_id=user_id,
                    name=payload.name,
                    asset_type=payload.asset_type,
                    category=payload.category,
                    liquidity_tier=payload.liquidity_tier,
                )
                session.add(asset)
                await session.flush()

                session.add(CryptoHolding(
                    user_id=user_id,
                    asset_id=asset.id,
                    coingecko_id=payload.coingecko_id,
                    symbol=payload.symbol,
                    quantity=add_qty,
                    avg_buy_price=add_price,
                ))
                session.add(Transaction(
                    user_id=user_id,
                    asset_id=asset.id,
                    transaction_type="BUY",
                    transaction_date=date.today(),
                    amount=add_qty * add_price,
                    units=add_qty,
                    price_per_unit=add_price,
                ))
                invested = add_qty * add_price
                await _write_initial_valuation(session, user_id, asset.id, invested, invested, Decimal("0"))
                await _complete_onboarding(session, user_id)
                await session.commit()
                await session.refresh(asset)
                return _asset_row(asset)
            except IntegrityError:
                # A concurrent request committed the same holding first.
                # Our transaction (including the orphaned Asset row) was rolled back.
                await session.rollback()
                existing_result = await session.execute(
                    select(CryptoHolding).where(
                        and_(
                            CryptoHolding.coingecko_id == payload.coingecko_id,
                            CryptoHolding.user_id == user_id,
                        )
                    )
                )
                existing = existing_result.scalar_one()

        # Merge into existing holding (reached on first pass or after race retry).
        old_qty = existing.quantity
        old_avg = existing.avg_buy_price
        total_qty = old_qty + add_qty
        if total_qty > 0:
            existing.avg_buy_price = (old_qty * old_avg + add_qty * add_price) / total_qty
        existing.quantity = total_qty
        new_avg = Decimal(str(existing.avg_buy_price))

        session.add(Transaction(
            user_id=user_id,
            asset_id=existing.asset_id,
            transaction_type="BUY",
            transaction_date=date.today(),
            amount=add_qty * add_price,
            units=add_qty,
            price_per_unit=add_price,
        ))
        invested = Decimal(str(total_qty)) * new_avg
        await _write_initial_valuation(session, user_id, existing.asset_id, invested, invested, Decimal("0"))
        await _complete_onboarding(session, user_id)
        await session.commit()

        asset_result = await session.execute(
            select(Asset).where(Asset.id == existing.asset_id)
        )
        return _asset_row(asset_result.scalar_one())

    # ── MUTUAL FUND ──────────────────────────────────────────────────────────
    if payload.asset_type == "MUTUAL_FUND":
        if not payload.scheme_code or payload.amount_invested is None or payload.nav_at_purchase is None:
            raise HTTPException(
                status_code=400,
                detail="Mutual fund requires scheme_code, amount_invested, and nav_at_purchase",
            )

        add_nav = payload.nav_at_purchase
        if add_nav <= 0:
            raise HTTPException(status_code=400, detail="NAV must be greater than zero")

        add_units = payload.amount_invested / add_nav
        add_amount = payload.amount_invested

        existing_result = await session.execute(
            select(MutualFundHolding).where(
                and_(
                    MutualFundHolding.scheme_code == payload.scheme_code,
                    MutualFundHolding.user_id == user_id,
                )
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is None:
            try:
                asset = Asset(
                    user_id=user_id,
                    name=payload.name,
                    asset_type=payload.asset_type,
                    category=payload.category,
                    liquidity_tier=payload.liquidity_tier,
                )
                session.add(asset)
                await session.flush()

                session.add(MutualFundHolding(
                    user_id=user_id,
                    asset_id=asset.id,
                    scheme_code=payload.scheme_code,
                    units=add_units,
                    nav_at_purchase=add_nav,
                    monthly_sip=payload.monthly_sip,
                ))
                session.add(Transaction(
                    user_id=user_id,
                    asset_id=asset.id,
                    transaction_type="BUY",
                    transaction_date=date.today(),
                    amount=add_amount,
                    units=add_units,
                    price_per_unit=add_nav,
                ))
                await _write_initial_valuation(session, user_id, asset.id, add_amount, add_amount, Decimal("0"))
                await _complete_onboarding(session, user_id)
                await session.commit()
                await session.refresh(asset)
                return _asset_row(asset)
            except IntegrityError:
                # A concurrent request committed the same holding first.
                # Our transaction (including the orphaned Asset row) was rolled back.
                await session.rollback()
                existing_result = await session.execute(
                    select(MutualFundHolding).where(
                        and_(
                            MutualFundHolding.scheme_code == payload.scheme_code,
                            MutualFundHolding.user_id == user_id,
                        )
                    )
                )
                existing = existing_result.scalar_one()

        # Merge into existing holding (reached on first pass or after race retry).
        old_units = existing.units
        old_nav = existing.nav_at_purchase
        total_units = old_units + add_units
        if total_units > 0:
            existing.nav_at_purchase = (old_units * old_nav + add_units * add_nav) / total_units
        existing.units = total_units
        if payload.monthly_sip:
            existing.monthly_sip = payload.monthly_sip

        session.add(Transaction(
            user_id=user_id,
            asset_id=existing.asset_id,
            transaction_type="BUY",
            transaction_date=date.today(),
            amount=add_amount,
            units=add_units,
            price_per_unit=add_nav,
        ))
        total_invested = Decimal(str(total_units)) * Decimal(str(existing.nav_at_purchase))
        await _write_initial_valuation(session, user_id, existing.asset_id, total_invested, total_invested, Decimal("0"))
        await _complete_onboarding(session, user_id)
        await session.commit()

        asset_result = await session.execute(
            select(Asset).where(Asset.id == existing.asset_id)
        )
        return _asset_row(asset_result.scalar_one())

    # ── FIXED INCOME (FD / RD / PPF) ────────────────────────────────────────
    if payload.asset_type in FI_TYPES:
        if payload.principal is None or payload.annual_rate is None or payload.start_date is None:
            raise HTTPException(
                status_code=400,
                detail=f"{payload.asset_type} requires principal, annual_rate, and start_date",
            )

        freq = payload.compounding_frequency or "YEARLY"
        today = date.today()

        if payload.asset_type == "RD":
            months = _rd_months_elapsed(payload.start_date, today)
            fi_invested = payload.principal * Decimal(months)
            fi_current = rd_current_value(payload.principal, payload.annual_rate, payload.start_date, today, freq)
        else:
            fi_invested = payload.principal
            fi_current = compound_value(fi_invested, payload.annual_rate, payload.start_date, today, freq)

        asset = Asset(
            user_id=user_id,
            name=payload.name,
            asset_type=payload.asset_type,
            category=payload.category,
            liquidity_tier=payload.liquidity_tier,
        )
        session.add(asset)
        await session.flush()

        session.add(FixedIncomeHolding(
            user_id=user_id,
            asset_id=asset.id,
            principal=payload.principal,
            annual_rate=payload.annual_rate,
            start_date=payload.start_date,
            maturity_date=payload.maturity_date,
            compounding_frequency=freq,
        ))
        session.add(Transaction(
            user_id=user_id,
            asset_id=asset.id,
            transaction_type="DEPOSIT",
            transaction_date=payload.start_date,
            amount=payload.principal,
            units=None,
            price_per_unit=None,
        ))
        await _write_initial_valuation(session, user_id, asset.id, fi_invested, fi_current, fi_current - fi_invested)
        await _complete_onboarding(session, user_id)
        await session.commit()
        await session.refresh(asset)
        return _asset_row(asset)

    # ── MANUAL ───────────────────────────────────────────────────────────────
    if payload.asset_type == "MANUAL":
        if payload.cost_basis is None or payload.current_value is None:
            raise HTTPException(
                status_code=400,
                detail="Manual asset requires cost_basis (what you paid) and current_value (estimated value today)",
            )

        asset = Asset(
            user_id=user_id,
            name=payload.name,
            asset_type="MANUAL",
            category=payload.category,
            liquidity_tier=payload.liquidity_tier,
        )
        session.add(asset)
        await session.flush()

        session.add(ManualHolding(
            user_id=user_id,
            asset_id=asset.id,
            cost_basis=payload.cost_basis,
            current_value=payload.current_value,
            notes=payload.notes,
        ))
        pnl = payload.current_value - payload.cost_basis
        await _write_initial_valuation(session, user_id, asset.id, payload.cost_basis, payload.current_value, pnl, source="manual")
        await _complete_onboarding(session, user_id)
        await session.commit()
        await session.refresh(asset)
        return _asset_row(asset)

    # ── OTHER ────────────────────────────────────────────────────────────────
    asset = Asset(
        user_id=user_id,
        name=payload.name,
        asset_type=payload.asset_type,
        category=payload.category,
        liquidity_tier=payload.liquidity_tier,
    )
    session.add(asset)
    await _complete_onboarding(session, user_id)
    await session.commit()
    await session.refresh(asset)
    return _asset_row(asset)


@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: str,
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    result = await session.execute(
        select(Asset).where(and_(Asset.id == asset_id, Asset.user_id == user_id))
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    await session.delete(asset)
    await session.commit()
    return {"deleted": True, "asset_id": asset_id}


class CryptoSellRequest(BaseModel):
    quantity: Decimal = Field(gt=0)


@router.post("/assets/{asset_id}/sell-crypto")
async def sell_crypto(
    asset_id: str,
    payload: CryptoSellRequest,
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    result = await session.execute(
        select(CryptoHolding).where(
            and_(CryptoHolding.asset_id == asset_id, CryptoHolding.user_id == user_id)
        )
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
        user_id=user_id,
        asset_id=holding.asset_id,
        transaction_type="SELL",
        transaction_date=date.today(),
        amount=payload.quantity * holding.avg_buy_price,
        units=payload.quantity,
        price_per_unit=holding.avg_buy_price,
    ))
    await session.commit()

    return {"asset_id": asset_id, "remaining_quantity": float(holding.quantity)}


class MFRedeemRequest(BaseModel):
    units: Decimal = Field(gt=0)


@router.post("/assets/{asset_id}/redeem-mf")
async def redeem_mf(
    asset_id: str,
    payload: MFRedeemRequest,
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    result = await session.execute(
        select(MutualFundHolding).where(
            and_(MutualFundHolding.asset_id == asset_id, MutualFundHolding.user_id == user_id)
        )
    )
    holding = result.scalar_one_or_none()

    if not holding:
        raise HTTPException(status_code=404, detail="Mutual fund holding not found")
    if payload.units <= 0:
        raise HTTPException(status_code=400, detail="Redeem units must be positive")
    if payload.units > holding.units:
        raise HTTPException(status_code=400, detail="Cannot redeem more than held units")

    holding.units = holding.units - payload.units

    session.add(Transaction(
        user_id=user_id,
        asset_id=holding.asset_id,
        transaction_type="SELL",
        transaction_date=date.today(),
        amount=payload.units * holding.nav_at_purchase,
        units=payload.units,
        price_per_unit=holding.nav_at_purchase,
    ))
    await session.commit()

    return {"asset_id": asset_id, "remaining_units": float(holding.units)}


class TopUpRequest(BaseModel):
    amount: Decimal = Field(gt=0)


@router.post("/assets/{asset_id}/top-up")
async def top_up_savings(
    asset_id: str,
    payload: TopUpRequest,
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    asset_result = await session.execute(
        select(Asset).where(and_(Asset.id == asset_id, Asset.user_id == user_id))
    )
    asset = asset_result.scalar_one_or_none()
    if not asset or asset.asset_type not in {"SAVINGS_ACC", "PPF"}:
        raise HTTPException(status_code=404, detail="Asset does not support top-up")
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Top-up amount must be positive")

    fi_result = await session.execute(
        select(FixedIncomeHolding).where(
            and_(FixedIncomeHolding.asset_id == asset_id, FixedIncomeHolding.user_id == user_id)
        )
    )
    holding = fi_result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding record not found")

    holding.principal = holding.principal + payload.amount
    new_principal = Decimal(str(holding.principal))

    session.add(Transaction(
        user_id=user_id,
        asset_id=asset_id,
        transaction_type="DEPOSIT",
        transaction_date=date.today(),
        amount=payload.amount,
        units=None,
        price_per_unit=None,
    ))

    fi_current = compound_value(new_principal, Decimal(str(holding.annual_rate)), holding.start_date, date.today(), holding.compounding_frequency)
    await _write_initial_valuation(session, user_id, asset_id, new_principal, fi_current, fi_current - new_principal)
    await session.commit()

    return {"asset_id": asset_id, "new_principal": float(new_principal)}
