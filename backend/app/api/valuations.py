from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import ValuationHistory
from app.services.valuation import recalculate_crypto_valuations

router = APIRouter()


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/valuations/recalculate")
async def recalculate(session=Depends(get_session)):
    crypto = await recalculate_crypto_valuations(session)
    return {"crypto": crypto}


@router.get("/valuations/latest")
async def latest_valuations(session=Depends(get_session)):
    result = await session.execute(select(ValuationHistory))
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
