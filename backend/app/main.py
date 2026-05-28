from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.init_db import init_db
from app.api.dashboard import router as dashboard_router
from app.api.assets import router as assets_router
from app.api.insights import router as insights_router

from app.core.config import settings
from app.jobs.scheduler import start_scheduler

from app.api.valuations import router as valuations_router
from app.api.market import router as market_router
from app.api.snapshots import router as snapshots_router
from app.api.transactions import router as transactions_router

app = FastAPI(title="Investment Observability API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://172.23.80.6:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()
    if settings.scheduler_enabled:
        start_scheduler()


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(dashboard_router)
app.include_router(assets_router)
app.include_router(insights_router)
app.include_router(valuations_router)
app.include_router(market_router)
app.include_router(snapshots_router)
app.include_router(transactions_router)


