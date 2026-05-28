from datetime import date
from decimal import Decimal
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ValuationHistory, PortfolioSnapshot


async def get_dashboard(session: AsyncSession) -> dict:
    # Latest valuation per asset only — prevents double-counting across multiple recalculate calls
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

    total_invested = sum(Decimal(str(v.invested_amount)) for v in valuations)
    total_value = sum(Decimal(str(v.current_value)) for v in valuations)
    total_pnl = total_value - total_invested

    return {
        "total_invested": float(total_invested),
        "total_value": float(total_value),
        "total_pnl": float(total_pnl),
        "pnl_percent": float((total_pnl / total_invested) * 100) if total_invested else 0.0,
    }


async def create_or_update_snapshot(session: AsyncSession) -> PortfolioSnapshot:
    """Upsert today's snapshot — safe to call multiple times per day."""
    dashboard = await get_dashboard(session)
    today = date.today()

    await session.execute(
        delete(PortfolioSnapshot).where(PortfolioSnapshot.snapshot_date == today)
    )
    snapshot = PortfolioSnapshot(
        snapshot_date=today,
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
