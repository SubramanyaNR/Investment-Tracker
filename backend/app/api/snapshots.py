from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import PortfolioSnapshot

router = APIRouter()


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/snapshots")
async def list_snapshots(session=Depends(get_session)):
    result = await session.execute(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date.asc())
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
