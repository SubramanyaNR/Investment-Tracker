from decimal import Decimal
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from app.db.session import AdminSessionLocal
from app.db.models import Asset, MutualFundHolding, Transaction
from app.integrations.mfapi import get_latest_nav
from app.services.portfolio import create_or_update_snapshot


scheduler = AsyncIOScheduler()


async def daily_snapshot_job():
    async with AdminSessionLocal() as session:
        result = await session.execute(select(Asset.user_id).distinct())
        user_ids = result.scalars().all()
        for user_id in user_ids:
            await create_or_update_snapshot(session, user_id)


async def monthly_sip_job():
    """Runs 1st of each month — buys new units at current NAV for all active SIPs."""
    async with AdminSessionLocal() as session:
        result = await session.execute(
            select(Asset, MutualFundHolding)
            .join(MutualFundHolding, MutualFundHolding.asset_id == Asset.id)
            .where(MutualFundHolding.monthly_sip > 0)
        )
        rows = result.all()
        if not rows:
            return

        for asset, holding in rows:
            try:
                nav_data = await get_latest_nav(holding.scheme_code)
                current_nav = Decimal(str(nav_data["nav"]))
            except Exception:
                continue

            sip_amount = Decimal(str(holding.monthly_sip))
            new_units = sip_amount / current_nav

            old_units = holding.units
            old_nav = holding.nav_at_purchase
            total_units = old_units + new_units
            if total_units > 0:
                holding.nav_at_purchase = (old_units * old_nav + new_units * current_nav) / total_units
            holding.units = total_units

            session.add(Transaction(
                user_id=holding.user_id,
                asset_id=holding.asset_id,
                transaction_type="BUY",
                transaction_date=date.today(),
                amount=sip_amount,
                units=new_units,
                price_per_unit=current_nav,
            ))

        await session.commit()


def start_scheduler():
    scheduler.add_job(daily_snapshot_job, "cron", hour=23, minute=55)
    scheduler.add_job(monthly_sip_job, "cron", day=1, hour=9, minute=0)
    scheduler.start()
