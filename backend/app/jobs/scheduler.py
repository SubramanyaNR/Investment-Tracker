from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.session import AsyncSessionLocal
from app.services.portfolio import create_snapshot


scheduler = AsyncIOScheduler()


async def daily_snapshot_job():
    async with AsyncSessionLocal() as session:
        await create_snapshot(session)


def start_scheduler():
    scheduler.add_job(daily_snapshot_job, "cron", hour=23, minute=55)
    scheduler.start()
