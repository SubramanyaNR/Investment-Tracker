from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from app.db.session import AsyncSessionLocal
from app.db.models import ValuationHistory
from app.services.valuation import (
    recalculate_crypto_valuations,
    recalculate_fixed_income_valuations,
    recalculate_mf_valuations,
)
from app.services.portfolio import create_or_update_snapshot

router = APIRouter()


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/valuations/recalculate")
async def recalculate(session=Depends(get_session)):
    crypto = await recalculate_crypto_valuations(session)
    fi = await recalculate_fixed_income_valuations(session)
    mf = await recalculate_mf_valuations(session)
    await create_or_update_snapshot(session)
    return {"crypto": crypto, "fixed_income": fi, "mutual_funds": mf}


@router.get("/valuations/latest")
async def latest_valuations(session=Depends(get_session)):
    subq = (
        select(
            ValuationHistory.asset_id,
            func.max(ValuationHistory.valuation_date).label("latest_date"),
        )
        .group_by(ValuationHistory.asset_id)
        .subquery()
    )
    result = await session.execute(
        select(ValuationHistory).join(
            subq,
            and_(
                ValuationHistory.asset_id == subq.c.asset_id,
                ValuationHistory.valuation_date == subq.c.latest_date,
            ),
        )
    )
    valuations = result.scalars().all()
    return [
        {
            "asset_id": str(v.asset_id),
            "valuation_date": str(v.valuation_date),
            "invested_amount": float(v.invested_amount),
            "current_value": float(v.current_value),
            "pnl": float(v.pnl),
            "source": v.source,
        }
        for v in valuations
    ]
