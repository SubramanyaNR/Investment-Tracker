import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.dashboard import router as dashboard_router
from app.api.assets import router as assets_router
from app.api.insights import router as insights_router

from app.core.config import settings
from app.core.observability import log_event, redact
from app.core.ratelimit import rate_limit_user
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


@app.middleware("http")
async def access_log(request: Request, call_next):
    req_id = uuid.uuid4().hex[:8]
    request.state.req_id = req_id
    start = time.monotonic()
    response = await call_next(request)
    dur_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Request-Id"] = req_id
    log_event(
        "request", req_id=req_id, method=request.method, path=request.url.path,
        status=response.status_code, dur_ms=dur_ms,
        user=getattr(request.state, "user_id", "anon"),  # stamped by get_session on authed routes
    )
    return response


@app.exception_handler(Exception)
async def log_unhandled(request: Request, exc: Exception):
    log_event(
        "error", req_id=getattr(request.state, "req_id", "-"), path=request.url.path,
        type=type(exc).__name__, msg=redact(str(exc)),
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


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


