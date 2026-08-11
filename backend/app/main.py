import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.auth import bootstrap_admin_user, router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.assets import router as assets_router
from app.api.insights import router as insights_router

from app.core.auth import csrf_check
from app.core.config import settings
from app.core.observability import log_event, redact
from app.core.ratelimit import rate_limit_user
from app.jobs.scheduler import start_scheduler

from app.api.valuations import router as valuations_router
from app.api.market import router as market_router
from app.api.snapshots import router as snapshots_router
from app.api.transactions import router as transactions_router
from app.api.account import router as account_router
from app.api.importer import router as importer_router, public_router as importer_public_router
from app.api.xirr import router as xirr_router
from app.api.performance import router as performance_router
from app.api.export import router as export_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic — run `alembic upgrade head` on deploy, not here.
    await bootstrap_admin_user()
    if settings.scheduler_enabled:
        start_scheduler()
    yield


app = FastAPI(title="Investment Observability API", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    # Double-submit cookie: applies globally so no router individually opts in
    # or forgets to. /auth/login is exempt (no session exists yet to compare
    # against); every other unsafe-method request must present a matching pair.
    # Caught and converted here rather than left to bubble up — HTTPExceptions
    # raised inside @app.middleware("http") aren't reliably caught by FastAPI's
    # route-level exception handling.
    try:
        csrf_check(
            request.method,
            request.url.path,
            request.cookies.get("access_token") is not None,
            request.cookies.get("csrf_token"),
            request.headers.get("x-csrf-token"),
        )
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


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


@app.get("/health")
async def health():
    return {"status": "ok"}


# Per-user rate limit on every authenticated router (keyed on JWT sub). Heavier
# routes (recalculate, insights/refresh) add a tighter per-endpoint limit in-place.
# /market/* is public and rate-limited per-IP inside its router.
_per_user = [Depends(rate_limit_user("rl_user_general", "general"))]

app.include_router(auth_router)   # public: login must be reachable pre-auth; own IP rate limit
app.include_router(dashboard_router, dependencies=_per_user)
app.include_router(assets_router, dependencies=_per_user)
app.include_router(insights_router, dependencies=_per_user)
app.include_router(valuations_router, dependencies=_per_user)
app.include_router(market_router)
app.include_router(importer_public_router)           # public: template download, IP rate-limited
app.include_router(snapshots_router, dependencies=_per_user)
app.include_router(transactions_router, dependencies=_per_user)
app.include_router(account_router, dependencies=_per_user)
app.include_router(importer_router, dependencies=_per_user)
app.include_router(xirr_router, dependencies=_per_user)
app.include_router(performance_router, dependencies=_per_user)
app.include_router(export_router, dependencies=_per_user)


