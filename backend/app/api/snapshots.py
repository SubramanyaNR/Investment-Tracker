import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.api.deps import get_session
from app.db.models import PortfolioSnapshot
from app.core.auth import get_current_user_id

router = APIRouter()


@router.get("/snapshots")
async def list_snapshots(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    result = await session.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == user_id)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
    )
    snapshots = result.scalars().all()
    return [
        {
            "snapshot_date": str(s.snapshot_date),
            "total_invested": float(s.total_invested),
            "total_value": float(s.total_value),
            "total_pnl": float(s.total_pnl),
        }
        for s in snapshots
    ]
