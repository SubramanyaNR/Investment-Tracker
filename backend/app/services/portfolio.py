from datetime import date
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Asset, Transaction, ValuationHistory, PortfolioSnapshot


async def get_dashboard(session: AsyncSession) -> dict:
    result = await session.execute(select(ValuationHistory))
    valuations = result.scalars().all()

    total_invested = sum(Decimal(v.invested_amount) for v in valuations)
    total_value = sum(Decimal(v.current_value) for v in valuations)
    total_pnl = total_value - total_invested

    return {
        "total_invested": float(total_invested),
        "total_value": float(total_value),
        "total_pnl": float(total_pnl),
        "pnl_percent": float((total_pnl / total_invested) * 100) if total_invested else 0,
    }


async def create_snapshot(session: AsyncSession) -> PortfolioSnapshot:
    dashboard = await get_dashboard(session)

    snapshot = PortfolioSnapshot(
        snapshot_date=date.today(),
        total_invested=dashboard["total_invested"],
        total_value=dashboard["total_value"],
        total_pnl=dashboard["total_pnl"],
        allocation={},
        liquidity={},
        metrics=dashboard,
    )

    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)
    return snapshot
