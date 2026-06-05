from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.dashboard import router as dashboard_router
from app.api.assets import router as assets_router
from app.api.insights import router as insights_router

from app.core.config import settings
from app.core.ratelimit import rate_limit_user  # imports observability -> configures logger
from app.jobs.scheduler import start_scheduler

from app.api.valuations import router as valuations_router
from app.api.market import router as market_router
from app.api.snapshots import router as snapshots_router
from app.api.transactions import router as transactions_router
from app.api.account import router as account_router

app = FastAPI(title="Investment Observability API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    # Schema is managed by Alembic — run `alembic upgrade head` on deploy, not here.
    if settings.scheduler_enabled:
        start_scheduler()


@app.get("/health")
async def health():
    return {"status": "ok"}


# Per-user rate limit on every authenticated router (keyed on JWT sub). Heavier
# routes (recalculate, insights/refresh) add a tighter per-endpoint limit in-place.
# /market/* is public and rate-limited per-IP inside its router.
_per_user = [Depends(rate_limit_user("rl_user_general", "general"))]

app.include_router(dashboard_router, dependencies=_per_user)
app.include_router(assets_router, dependencies=_per_user)
app.include_router(insights_router, dependencies=_per_user)
app.include_router(valuations_router, dependencies=_per_user)
app.include_router(market_router)
app.include_router(snapshots_router, dependencies=_per_user)
app.include_router(transactions_router, dependencies=_per_user)
app.include_router(account_router, dependencies=_per_user)


