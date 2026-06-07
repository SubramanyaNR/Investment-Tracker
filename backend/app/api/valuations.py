import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from app.api.deps import get_session
from app.db.models import ValuationHistory
from app.services.valuation import (
    recalculate_crypto_valuations,
    recalculate_fixed_income_valuations,
    recalculate_manual_valuations,
    recalculate_mf_valuations,
)
from app.services.portfolio import create_or_update_snapshot
from app.core.auth import get_current_user_id
from app.core.ratelimit import rate_limit_user

router = APIRouter()


@router.post(
    "/valuations/recalculate",
    dependencies=[Depends(rate_limit_user("rl_user_recalculate", "recalc"))],
)
async def recalculate(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    crypto = await recalculate_crypto_valuations(session, user_id)
    fi = await recalculate_fixed_income_valuations(session, user_id)
    mf = await recalculate_mf_valuations(session, user_id)
    await recalculate_manual_valuations(session, user_id)
    await create_or_update_snapshot(session, user_id)
    return {"crypto": crypto, "fixed_income": fi, "mutual_funds": mf}


@router.get("/valuations/latest")
async def latest_valuations(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    subq = (
        select(
            ValuationHistory.asset_id,
            func.max(ValuationHistory.valuation_date).label("latest_date"),
        )
        .where(ValuationHistory.user_id == user_id)
        .group_by(ValuationHistory.asset_id)
        .subquery()
    )
    result = await session.execute(
        select(ValuationHistory)
        .where(ValuationHistory.user_id == user_id)
        .join(
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
