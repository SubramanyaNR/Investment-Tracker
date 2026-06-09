"""Performance ranking router — F9 (monthly) + F10 (daily).

GET /performance/monthly  → top/bottom 3 performers this calendar month
GET /performance/daily    → top/bottom 3 performers vs yesterday
"""
import uuid
from fastapi import APIRouter, Depends

from app.api.deps import get_session
from app.core.auth import get_current_user_id
from app.core.ratelimit import rate_limit_user
from app.services.performance import monthly_performance, daily_performance

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get(
    "/monthly",
    dependencies=[Depends(rate_limit_user("rl_user_performance", "perf_monthly"))],
)
async def get_monthly_performance(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Top/bottom 3 CRYPTO + MF performers for the current calendar month."""
    return await monthly_performance(session, user_id)


@router.get(
    "/daily",
    dependencies=[Depends(rate_limit_user("rl_user_performance", "perf_daily"))],
)
async def get_daily_performance(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Top/bottom 3 CRYPTO + MF performers vs yesterday.

    Returns has_data=False gracefully when yesterday's valuation rows
    are absent (nightly recalculate job not yet run or first use).
    """
    return await daily_performance(session, user_id)
