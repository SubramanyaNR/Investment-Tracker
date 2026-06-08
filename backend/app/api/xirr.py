"""XIRR router — F5.

GET /xirr → portfolio-level and per-asset XIRR for the authenticated user.
"""
import uuid
from fastapi import APIRouter, Depends

from app.api.deps import get_session
from app.core.auth import get_current_user_id
from app.core.ratelimit import rate_limit_user
from app.services.xirr import compute_xirr

router = APIRouter(tags=["xirr"])


@router.get(
    "/xirr",
    dependencies=[Depends(rate_limit_user("rl_user_xirr", "xirr"))],
)
async def get_xirr(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Return XIRR for the portfolio and each individual asset.

    Returns null XIRR values when data is insufficient (< 2 cash flows,
    identical dates, or no convergence). Manual assets are excluded from
    all calculations; manual_assets_excluded flag is set if any exist.
    """
    return await compute_xirr(session, user_id)
