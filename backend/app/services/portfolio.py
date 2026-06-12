import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ValuationHistory, PortfolioSnapshot, User, Asset


async def get_dashboard(session: AsyncSession, user_id: uuid.UUID) -> dict:
    # Latest valuation per asset only — prevents double-counting across multiple recalculate calls
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

    total_invested = sum(Decimal(str(v.invested_amount)) for v in valuations)
    total_value = sum(Decimal(str(v.current_value)) for v in valuations)
    total_pnl = total_value - total_invested

    # Onboarding eligibility: 0 assets AND (user record missing OR onboarding_completed is False)
    asset_count_result = await session.execute(
        select(func.count(Asset.id)).where(Asset.user_id == user_id)
    )
    asset_count = asset_count_result.scalar() or 0

    user_result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    onboarding_completed = user.onboarding_completed if user else False
    is_onboarding_eligible = (asset_count == 0) and not onboarding_completed

    return {
        "total_invested": float(total_invested),
        "total_value": float(total_value),
        "total_pnl": float(total_pnl),
        "pnl_percent": float((total_pnl / total_invested) * 100) if total_invested else 0.0,
        "is_onboarding_eligible": is_onboarding_eligible,
    }


async def create_or_update_snapshot(session: AsyncSession, user_id: uuid.UUID) -> PortfolioSnapshot:
    """Upsert today's snapshot — atomic under concurrent calls."""
    dashboard = await get_dashboard(session, user_id)
    today = date.today()

    stmt = (
        pg_insert(PortfolioSnapshot)
        .values(
            id=uuid.uuid4(),
            user_id=user_id,
            snapshot_date=today,
            total_invested=dashboard["total_invested"],
            total_value=dashboard["total_value"],
            total_pnl=dashboard["total_pnl"],
            allocation={},
            liquidity={},
            metrics=dashboard,
        )
        .on_conflict_do_update(
            index_elements=["user_id", "snapshot_date"],
            set_=dict(
                total_invested=dashboard["total_invested"],
                total_value=dashboard["total_value"],
                total_pnl=dashboard["total_pnl"],
                metrics=dashboard,
            ),
        )
        .returning(PortfolioSnapshot)
    )
    result = await session.scalars(stmt)
    await session.commit()
    return result.one()
