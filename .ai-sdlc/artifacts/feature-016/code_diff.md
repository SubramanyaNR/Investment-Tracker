## Modified Files (git diff HEAD)

```diff
diff --git a/backend/app/api/account.py b/backend/app/api/account.py
index 1e71c79..35b086e 100644
--- a/backend/app/api/account.py
+++ b/backend/app/api/account.py
@@ -13,11 +13,11 @@ async def delete_account(
     session=Depends(get_session),
     user_id: uuid.UUID = Depends(get_current_user_id),
 ):
     """Purge all of the caller's data. Deleting assets cascades to transactions,
     valuations and holdings; snapshots and insights aren't asset-linked so are
-    removed explicitly. Does not delete the Supabase auth user (admin API)."""
+    removed explicitly. Does not delete the user's login/admin account row."""
     await session.execute(delete(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user_id))
     await session.execute(delete(AIInsight).where(AIInsight.user_id == user_id))
     await session.execute(delete(Asset).where(Asset.user_id == user_id))
     await session.commit()
     return {"deleted": True}
diff --git a/backend/app/api/assets.py b/backend/app/api/assets.py
index 698e17b..f6ed927 100644
--- a/backend/app/api/assets.py
+++ b/backend/app/api/assets.py
@@ -1,29 +1,29 @@
 import uuid
 from decimal import Decimal
 from datetime import date
 from fastapi import APIRouter, Depends, HTTPException, Query
 from pydantic import BaseModel, Field, field_validator
-from sqlalchemy import select, delete, and_, func
-from sqlalchemy.dialects.postgresql import insert as pg_insert
+from sqlalchemy import select, delete, and_, func, update
 from sqlalchemy.exc import IntegrityError
 from typing import Optional
 from app.api.deps import get_session
 from app.db.models import Asset, CryptoHolding, FixedIncomeHolding, ManualHolding, MutualFundHolding, Transaction, ValuationHistory, User
 
 
 async def _complete_onboarding(session, user_id: uuid.UUID) -> None:
-    """Mark onboarding as completed for the user — idempotent upsert."""
-    stmt = (
-        pg_insert(User)
-        .values(id=user_id, onboarding_completed=True)
-        .on_conflict_do_update(
-            index_elements=["id"],
-            set_=dict(onboarding_completed=True)
-        )
+    """Mark onboarding as completed for the user.
+
+    A plain UPDATE, not an upsert: the single-user model guarantees a `users`
+    row already exists (created at first-run bootstrap, required before any
+    caller can even reach this authenticated endpoint) with a real
+    `password_hash` — an upsert-INSERT here would violate that NOT NULL
+    column, since this function has no password to supply.
+    """
+    await session.execute(
+        update(User).where(User.id == user_id).values(onboarding_completed=True)
     )
-    await session.execute(stmt)
 from app.services.fixed_income import compound_value, rd_current_value
 from app.core.auth import get_current_user_id
 
 router = APIRouter()
 
diff --git a/backend/app/api/deps.py b/backend/app/api/deps.py
index 1a65234..4cd19aa 100644
--- a/backend/app/api/deps.py
+++ b/backend/app/api/deps.py
@@ -7,16 +7,15 @@ from app.db.session import AsyncSessionLocal
 
 
 async def get_session(request: Request, user_id: uuid.UUID = Depends(get_current_user_id)):
     """Request-scoped DB session bound to the caller's identity.
 
-    Stashing user_id in session.info lets the after_begin RLS hook set the
-    per-tenant GUC on every transaction this session opens; also stamps it on
-    request.state so the access log can attribute the request.
+    Stamps user_id on request.state so the access log can attribute the request.
+    Every query still filters by user_id explicitly at the app layer (RLS was
+    removed under architecture-002 Phase 2 — single-user model, no longer needed).
     """
     request.state.user_id = str(user_id)
     session = AsyncSessionLocal()
-    session.info["user_id"] = user_id
     try:
         yield session
     finally:
         await session.close()
diff --git a/backend/app/core/auth.py b/backend/app/core/auth.py
index 15cfbeb..6e686e0 100644
--- a/backend/app/core/auth.py
+++ b/backend/app/core/auth.py
@@ -1,83 +1,121 @@
+import hashlib
+import secrets
 import time
 import uuid
+from datetime import datetime, timedelta, timezone
 
+import bcrypt
 import jwt
-from fastapi import Depends, HTTPException
-from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
-from jwt import PyJWKClient, PyJWKClientConnectionError, PyJWKClientError, get_unverified_header
+from fastapi import Cookie, HTTPException
 
 from app.core.config import settings
 from app.core.observability import log_event
 
-# Supabase rotates its asymmetric signing keys; PyJWKClient caches the fetched
-# JWKS and re-fetches on an unknown kid, so rotation needs no redeploy.
-_jwk_client = PyJWKClient(settings.supabase_jwks_url, cache_keys=True)
+ACCESS_COOKIE = "access_token"
+REFRESH_COOKIE = "refresh_token"
+CSRF_COOKIE = "csrf_token"
 
-_bearer = HTTPBearer(auto_error=False)
 
-# kid -> monotonic() expiry. Only non-empty, confirmed-bad kids are stored.
-# Never cache empty-string: absence of a kid field is not evidence the kid is invalid.
-_negative_cache: dict[str, float] = {}
+# ── Password hashing ──────────────────────────────────────────────────────
 
-
-def _in_negative_cache(kid: str) -> bool:
-    entry = _negative_cache.get(kid)
-    if entry is None:
-        return False
-    if entry > time.monotonic():
-        return True
-    _negative_cache.pop(kid, None)   # lazy-evict expired entry
-    return False
+def hash_password(password: str) -> str:
+    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
 
 
-def _add_to_negative_cache(kid: str) -> None:
-    if len(_negative_cache) >= settings.jwks_negative_cache_maxsize:
-        _negative_cache.pop(next(iter(_negative_cache)), None)  # evict oldest
-    _negative_cache[kid] = time.monotonic() + settings.jwks_negative_cache_ttl
-
+def verify_password(password: str, password_hash: str) -> bool:
+    try:
+        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
+    except ValueError:
+        # Malformed hash (shouldn't happen outside a corrupted DB row) — fail closed.
+        return False
 
-def get_current_user_id(
-    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
-) -> uuid.UUID:
-    if credentials is None:
-        raise HTTPException(status_code=401, detail="Not authenticated")
 
-    token = credentials.credentials
+# ── Access token (short-lived JWT, HS256) ─────────────────────────────────
 
-    # Extract kid from the unverified header — pure base64/JSON parse, no network.
-    # DecodeError (malformed token) is a PyJWTError subclass; catch it early so the
-    # negative-cache check and JWKS path are never reached for garbage input.
-    try:
-        kid = get_unverified_header(token).get("kid") or ""
-    except jwt.PyJWTError:
-        raise HTTPException(status_code=401, detail="Invalid or expired token")
+def create_access_token(user_id: uuid.UUID) -> str:
+    now = datetime.now(timezone.utc)
+    claims = {
+        "sub": str(user_id),
+        "iat": now,
+        "exp": now + timedelta(seconds=settings.access_token_ttl_seconds),
+    }
+    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
 
-    # Short-circuit: kid already confirmed absent from JWKS — no upstream fetch needed.
-    # Empty kid is never cached: absence of a kid field ≠ confirmed bad kid.
-    if kid and _in_negative_cache(kid):
-        log_event("auth.negative_cache.hit", kid=kid[:8])
-        raise HTTPException(status_code=401, detail="Invalid or expired token")
 
-    # Generic 401 on every failure path — specific reason is an internal detail.
+def get_current_user_id(access_token: str | None = Cookie(default=None)) -> uuid.UUID:
+    if access_token is None:
+        raise HTTPException(status_code=401, detail="Not authenticated")
     try:
-        signing_key = _jwk_client.get_signing_key_from_jwt(token).key
         claims = jwt.decode(
-            token,
-            signing_key,
-            algorithms=["ES256"],
-            issuer=settings.supabase_issuer,
-            audience=settings.supabase_jwt_audience,
-            options={"require": ["exp", "sub", "iss", "aud"]},
+            access_token,
+            settings.jwt_secret,
+            algorithms=["HS256"],
+            options={"require": ["exp", "sub"]},
         )
         return uuid.UUID(claims["sub"])
-    except PyJWKClientConnectionError:
-        # Network failure reaching Supabase JWKS endpoint — do NOT cache negatively;
-        # the kid may be valid and the outage transient.
-        raise HTTPException(status_code=401, detail="Invalid or expired token")
-    except PyJWKClientError:
-        # kid confirmed absent from JWKS after a forced refresh — safe to cache.
-        if kid:
-            _add_to_negative_cache(kid)
+    except (jwt.PyJWTError, ValueError, TypeError):
         raise HTTPException(status_code=401, detail="Invalid or expired token")
-    except (jwt.PyJWTError, ValueError, TypeError) as exc:
-        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
+
+
+# ── Refresh token (opaque random value; only its SHA-256 hash is stored) ──
+# High-entropy random token, not a low-entropy password — a fast deterministic
+# hash (for direct DB lookup by hash) is the correct tool here, not bcrypt.
+
+def generate_refresh_token() -> tuple[str, str, datetime]:
+    """Returns (raw_token, token_hash, expires_at). Raw token goes in the cookie;
+    only the hash is ever persisted."""
+    raw = secrets.token_urlsafe(32)
+    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
+    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.refresh_token_ttl_seconds)
+    return raw, token_hash, expires_at
+
+
+def hash_refresh_token(raw_token: str) -> str:
+    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
+
+
+# ── CSRF (double-submit cookie) ────────────────────────────────────────────
+
+def generate_csrf_token() -> str:
+    return secrets.token_urlsafe(32)
+
+
+_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
+# No session exists yet when logging in, so there's nothing to double-submit against.
+_CSRF_EXEMPT_PATHS = {"/auth/login"}
+
+
+def csrf_check(
+    method: str, path: str, has_session: bool, cookie_value: str | None, header_value: str | None,
+) -> None:
+    """CSRF only matters when there's a session to ride on — an anonymous request
+    has no ambient authority to hijack, so it falls through to the normal 401 auth
+    gate instead of being intercepted here."""
+    if method not in _UNSAFE_METHODS or path in _CSRF_EXEMPT_PATHS or not has_session:
+        return
+    if not cookie_value or not header_value or not secrets.compare_digest(cookie_value, header_value):
+        log_event("auth.csrf.reject", path=path)
+        raise HTTPException(status_code=403, detail="CSRF check failed")
+
+
+# ── Cookie helpers ─────────────────────────────────────────────────────────
+
+def set_auth_cookies(response, *, access_token: str, refresh_token: str, csrf_token: str) -> None:
+    response.set_cookie(
+        ACCESS_COOKIE, access_token, max_age=settings.access_token_ttl_seconds,
+        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/",
+    )
+    response.set_cookie(
+        REFRESH_COOKIE, refresh_token, max_age=settings.refresh_token_ttl_seconds,
+        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/auth",
+    )
+    response.set_cookie(
+        CSRF_COOKIE, csrf_token, max_age=settings.access_token_ttl_seconds,
+        httponly=False, secure=settings.cookie_secure, samesite="lax", path="/",
+    )
+
+
+def clear_auth_cookies(response) -> None:
+    response.delete_cookie(ACCESS_COOKIE, path="/")
+    response.delete_cookie(REFRESH_COOKIE, path="/auth")
+    response.delete_cookie(CSRF_COOKIE, path="/")
diff --git a/backend/app/core/config.py b/backend/app/core/config.py
index a01d43b..de6ab37 100644
--- a/backend/app/core/config.py
+++ b/backend/app/core/config.py
@@ -16,18 +16,32 @@ class Settings(BaseSettings):
     ai_provider: str = "rules"
 
     gemini_api_key: str | None = None
     gemini_model: str = "gemini-2.0-flash"
 
-    supabase_jwks_url: str
-    supabase_issuer: str
-    supabase_jwt_audience: str = "authenticated"
-
     # DB TLS mode for asyncpg. Default "require" (Supabase). Set empty to disable
     # for a local non-TLS Postgres (e.g. the integration-test container).
     db_ssl: str | None = "require"
 
+    # ── architecture-002 Phase 2: custom auth (replaces Supabase Auth) ──────
+    # High-entropy secret, generated once, never committed. HS256 is the
+    # self-hosted-appropriate choice: no external JWKS verifier exists anymore.
+    jwt_secret: str
+    access_token_ttl_seconds: int = 900        # 15 min
+    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30  # 30 days
+    # First-run bootstrap only — creates the single admin user if `users` is
+    # empty. Not read again afterward; safe to leave in .env or remove post-bootstrap.
+    admin_email: str
+    admin_password: str
+    # Cookies must work over plain HTTP out of the box (self-host docker-compose
+    # up, and the founder's own plaintext access path) — Secure is opt-in for
+    # whoever puts real HTTPS in front (e.g. Tailscale), not a hardcoded default.
+    cookie_secure: bool = False
+    # Login attempts per IP per window (WINDOW=60s in ratelimit.py) — cheap
+    # brute-force insurance now that there's no email-based password reset.
+    rl_login_attempts: int = 5
+
     # ── A5: market caching + rate limiting ──────────────────────────────────
     rate_limit_enabled: bool = True
     # Backend binds 127.0.0.1 (reachable only via the proxy), so a proxy-set
     # X-Forwarded-For is trustworthy for client identification.
     trust_forwarded_for: bool = True
@@ -43,14 +57,10 @@ class Settings(BaseSettings):
     rl_user_insights: int = 6        # /insights/refresh (calls Gemini)
     rl_user_import: int = 5          # /import/csv (file parsing + DB writes)
     rl_user_xirr: int = 20           # /xirr (CPU-light but DB-read heavy)
     rl_user_performance: int = 30    # /performance/* (lightweight DB reads)
 
-    # ── A9: JWKS unknown-kid negative cache ─────────────────────────────────
-    jwks_negative_cache_ttl: int = 60        # seconds a confirmed-bad kid is remembered
-    jwks_negative_cache_maxsize: int = 1000  # cap memory; evict oldest on overflow
-
     class Config:
         env_file = ".env"
 
 
 settings = Settings()
diff --git a/backend/app/db/models.py b/backend/app/db/models.py
index 2946a9a..8dee9fc 100644
--- a/backend/app/db/models.py
+++ b/backend/app/db/models.py
@@ -1,6 +1,7 @@
 import uuid
+from datetime import datetime
 from sqlalchemy import String, Numeric, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, JSON, UniqueConstraint, func, Boolean
 from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
 from sqlalchemy.dialects.postgresql import UUID
 from typing import Optional
 
@@ -11,10 +12,24 @@ class Base(DeclarativeBase):
 
 class User(Base):
     __tablename__ = "users"
     id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
     onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
+    email: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)
+    password_hash: Mapped[str] = mapped_column(String, nullable=False)
+
+
+class RefreshToken(Base):
+    __tablename__ = "refresh_tokens"
+    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
+    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
+    # Never store the raw refresh token — only a hash, same principle as a password.
+    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
+    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
+    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
+    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
+    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
 
 
 class Asset(Base):
     __tablename__ = "assets"
     # Target for the child tables' composite (asset_id, user_id) FK — guarantees a
diff --git a/backend/app/db/session.py b/backend/app/db/session.py
index ab0dd06..d02e8d1 100644
--- a/backend/app/db/session.py
+++ b/backend/app/db/session.py
@@ -1,43 +1,20 @@
-from sqlalchemy import event, text
-from sqlalchemy.orm import Session as SyncSession
 from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
 from app.core.config import settings
 
 _connect_args = {"ssl": settings.db_ssl} if settings.db_ssl else {}
 
-# Request-path engine: connects as the non-superuser `app_user` role, which is
-# subject to Row-Level Security. Tenant scoping is enforced here as a backstop.
+# Request-path engine: connects as the least-privilege `app_user` role.
 engine = create_async_engine(
     settings.database_url,
     echo=False,
     connect_args=_connect_args,
 )
 AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
 
-# Admin engine: superuser role (BYPASSRLS) for the scheduler, which must operate
-# across all tenants. Migrations use this role too (see alembic/env.py).
+# Admin engine: superuser role for the scheduler and migrations (see alembic/env.py).
 admin_engine = create_async_engine(
     settings.admin_database_url,
     echo=False,
     connect_args=_connect_args,
 )
 AdminSessionLocal = async_sessionmaker(admin_engine, expire_on_commit=False)
-
-
-@event.listens_for(SyncSession, "after_begin")
-def _apply_rls_user(session, transaction, connection):
-    """Set the per-request RLS GUC at the start of every app-engine transaction.
-
-    LOCAL scope auto-clears at commit and never leaks across pooled connections;
-    re-applying it on each BEGIN keeps it set across mid-request commits. Sessions
-    on the admin engine (and a missing user_id) skip it and thus see no rows under
-    RLS — fail closed.
-    """
-    if connection.engine is not engine.sync_engine:
-        return
-    user_id = session.info.get("user_id")
-    if user_id is not None:
-        connection.execute(
-            text("SELECT set_config('app.current_user_id', :uid, true)"),
-            {"uid": str(user_id)},
-        )
diff --git a/backend/app/main.py b/backend/app/main.py
index 0b5485a..d1dbc8d 100644
--- a/backend/app/main.py
+++ b/backend/app/main.py
@@ -1,16 +1,18 @@
 import time
 import uuid
 from contextlib import asynccontextmanager
 
-from fastapi import Depends, FastAPI, Request
+from fastapi import Depends, FastAPI, HTTPException, Request
 from fastapi.middleware.cors import CORSMiddleware
 from fastapi.responses import JSONResponse
+from app.api.auth import bootstrap_admin_user, router as auth_router
 from app.api.dashboard import router as dashboard_router
 from app.api.assets import router as assets_router
 from app.api.insights import router as insights_router
 
+from app.core.auth import csrf_check
 from app.core.config import settings
 from app.core.observability import log_event, redact
 from app.core.ratelimit import rate_limit_user
 from app.jobs.scheduler import start_scheduler
 
@@ -26,10 +28,11 @@ from app.api.export import router as export_router
 
 
 @asynccontextmanager
 async def lifespan(app: FastAPI):
     # Schema is managed by Alembic — run `alembic upgrade head` on deploy, not here.
+    await bootstrap_admin_user()
     if settings.scheduler_enabled:
         start_scheduler()
     yield
 
 
@@ -43,10 +46,31 @@ app.add_middleware(
     allow_methods=["*"],
     allow_headers=["*"],
 )
 
 
+@app.middleware("http")
+async def csrf_middleware(request: Request, call_next):
+    # Double-submit cookie: applies globally so no router individually opts in
+    # or forgets to. /auth/login is exempt (no session exists yet to compare
+    # against); every other unsafe-method request must present a matching pair.
+    # Caught and converted here rather than left to bubble up — HTTPExceptions
+    # raised inside @app.middleware("http") aren't reliably caught by FastAPI's
+    # route-level exception handling.
+    try:
+        csrf_check(
+            request.method,
+            request.url.path,
+            request.cookies.get("access_token") is not None,
+            request.cookies.get("csrf_token"),
+            request.headers.get("x-csrf-token"),
+        )
+    except HTTPException as exc:
+        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
+    return await call_next(request)
+
+
 @app.middleware("http")
 async def access_log(request: Request, call_next):
     req_id = uuid.uuid4().hex[:8]
     request.state.req_id = req_id
     start = time.monotonic()
@@ -78,10 +102,11 @@ async def health():
 # Per-user rate limit on every authenticated router (keyed on JWT sub). Heavier
 # routes (recalculate, insights/refresh) add a tighter per-endpoint limit in-place.
 # /market/* is public and rate-limited per-IP inside its router.
 _per_user = [Depends(rate_limit_user("rl_user_general", "general"))]
 
+app.include_router(auth_router)   # public: login must be reachable pre-auth; own IP rate limit
 app.include_router(dashboard_router, dependencies=_per_user)
 app.include_router(assets_router, dependencies=_per_user)
 app.include_router(insights_router, dependencies=_per_user)
 app.include_router(valuations_router, dependencies=_per_user)
 app.include_router(market_router)
diff --git a/backend/requirements.txt b/backend/requirements.txt
index 866f91d..2dfc81d 100644
--- a/backend/requirements.txt
+++ b/backend/requirements.txt
@@ -2,10 +2,11 @@ alembic==1.18.4
 annotated-doc==0.0.4
 annotated-types==0.7.0
 anyio==4.13.0
 APScheduler==3.11.2
 asyncpg==0.31.0
+bcrypt==4.2.1
 certifi==2026.5.20
 cffi==2.0.0
 charset-normalizer==3.4.7
 click==8.4.1
 cryptography==48.0.0
diff --git a/backend/tests/conftest.py b/backend/tests/conftest.py
index 0b860eb..43f2cee 100644
--- a/backend/tests/conftest.py
+++ b/backend/tests/conftest.py
@@ -1,18 +1,18 @@
 """Test bootstrap.
 
 Sets hermetic dummy env vars BEFORE any `app.*` module is imported, so `Settings()`
-constructs without real secrets and no test touches Supabase, the database, or any
-external API. These take precedence over `backend/.env`, so the suite runs identically
-with or without a real `.env` present.
+constructs without real secrets and no test touches the database or any external API.
+These take precedence over `backend/.env`, so the suite runs identically with or
+without a real `.env` present.
 
-Unit tests (A3a) never open a connection — the SQLAlchemy engines and the Supabase
-JWKS client are created lazily, so dummy DSNs/URLs are sufficient. A3b will add real
-ephemeral-Postgres fixtures here for the integration tier.
+Unit tests (A3a) never open a connection — the SQLAlchemy engines are created lazily,
+so dummy DSNs are sufficient. A3b adds real ephemeral-Postgres fixtures for the
+integration tier.
 """
 import os
 
 os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
 os.environ.setdefault("ADMIN_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
-os.environ.setdefault("SUPABASE_JWKS_URL", "https://test.invalid/auth/v1/.well-known/jwks.json")
-os.environ.setdefault("SUPABASE_ISSUER", "https://test.invalid/auth/v1")
-os.environ.setdefault("SUPABASE_JWT_AUDIENCE", "authenticated")
+os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-a-real-secret")
+os.environ.setdefault("ADMIN_EMAIL", "admin@test.invalid")
+os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password-not-real")
diff --git a/backend/tests/integration/conftest.py b/backend/tests/integration/conftest.py
index 28fecd8..8c5ac97 100644
--- a/backend/tests/integration/conftest.py
+++ b/backend/tests/integration/conftest.py
@@ -1,13 +1,15 @@
-"""Integration-tier fixtures: an ephemeral Postgres with the real schema + RLS.
+"""Integration-tier fixtures: an ephemeral Postgres with the real schema.
 
-A session-scoped container is provisioned exactly like production: the non-superuser
-`app_user` role is created, then `alembic upgrade head` runs as admin with TLS off
-(DB_SSL="") to build the tables, RLS policies, grants, and FKs. The FastAPI app is
+A session-scoped container is provisioned exactly like production: the least-
+privilege `app_user` role is created, then `alembic upgrade head` runs as admin
+with TLS off (DB_SSL="") to build the tables, grants, and FKs. The FastAPI app is
 wired to the container by monkeypatching the request-path engine + session factory,
-so the production `get_session` and the per-transaction RLS GUC hook are exercised
-unchanged; only identity (`get_current_user_id`) is overridden per test.
+so the production `get_session` path is exercised unchanged; only identity
+(`get_current_user_id`) is overridden per test. Tenant isolation is enforced solely
+at the app layer (WHERE user_id = ...) — RLS was removed under architecture-002
+Phase 2 (single-user model).
 """
 import asyncio
 import os
 import subprocess
 import sys
@@ -51,12 +53,10 @@ def pg():
         asyncio.run(_create_role())
 
         env = {
             **os.environ,
             "ADMIN_DATABASE_URL": super_url, "DATABASE_URL": app_url, "DB_SSL": "",
-            "SUPABASE_JWKS_URL": "https://test.invalid/jwks", "SUPABASE_ISSUER": "https://test.invalid",
-            "SUPABASE_JWT_AUDIENCE": "authenticated",
         }
         r = subprocess.run([PY, "-m", "alembic", "upgrade", "head"], cwd=BACKEND,
                            env=env, capture_output=True, text=True)
         assert r.returncode == 0, f"alembic failed:\n{r.stdout}\n{r.stderr}"
 
diff --git a/backend/tests/integration/test_auth_jwt.py b/backend/tests/integration/test_auth_jwt.py
deleted file mode 100644
index 71540ae..0000000
--- a/backend/tests/integration/test_auth_jwt.py
+++ /dev/null
@@ -1,211 +0,0 @@
-"""JWT authentication matrix via HTTP endpoints — integration tests.
-
-Note: Unit-level JWT validation tests are in tests/unit/test_auth_verifier.py.
-This file tests the same matrix through actual HTTP endpoints to verify end-to-end
-authentication behavior.
-
-From SECURITY-AUDIT.md §7 (Auth matrix):
-- Valid token → 200
-- Expired token → 401
-- Wrong audience → 401
-- Wrong issuer → 401
-- Missing sub → 401
-- Missing exp → 401
-- Non-UUID sub → 401
-- alg=none → 401
-- alg=HS256 (key confusion) → 401
-- Tampered payload → 401
-- Unknown kid → 401
-- Real kid + forged signature → 401
-- Malformed header → 401
-- Missing header → 401
-
-This test file validates the integration: that invalid tokens are
-rejected consistently across all endpoints, not just one.
-"""
-import uuid
-from datetime import datetime, timedelta, timezone
-
-import jwt
-import pytest
-
-pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
-
-
-@pytest.fixture
-def jwt_secret():
-    """JWT secret for generating tokens."""
-    return "test-secret"
-
-
-def make_token(secret: str, **payload_overrides) -> str:
-    """Generate a JWT token with optional claim overrides."""
-    now = datetime.now(timezone.utc)
-    payload = {
-        "sub": str(uuid.uuid4()),
-        "aud": "authenticated",
-        "iss": "https://test.invalid/auth/v1",
-        "exp": int((now + timedelta(hours=1)).timestamp()),
-        "iat": int(now.timestamp()),
-        **payload_overrides,
-    }
-    return jwt.encode(payload, secret, algorithm="HS256")
-
-
-# ────────────────────────────────────────────────────────────────────────────
-# Valid token baseline
-# ────────────────────────────────────────────────────────────────────────────
-
-
-async def test_valid_token_accepted(anon_client, jwt_secret):
-    """Test: Valid JWT token is accepted → 200."""
-    token = make_token(jwt_secret)
-    resp = await anon_client.get(
-        "/health",  # Use public endpoint to avoid needing real user
-        headers={"Authorization": f"Bearer {token}"}
-    )
-    # Note: /health is public, so we just verify token is syntactically accepted
-    assert resp.status_code == 200
-
-
-# ────────────────────────────────────────────────────────────────────────────
-# Invalid tokens → 401 on protected endpoints
-# ────────────────────────────────────────────────────────────────────────────
-
-
-async def test_expired_token_rejected(anon_client, jwt_secret):
-    """Test: Expired token (exp in past) → 401."""
-    now = datetime.now(timezone.utc)
-    token = make_token(
-        jwt_secret,
-        exp=int((now - timedelta(hours=1)).timestamp())  # Expired 1h ago
-    )
-    resp = await anon_client.get(
-        "/dashboard",
-        headers={"Authorization": f"Bearer {token}"}
-    )
-    assert resp.status_code == 401
-
-
-async def test_wrong_audience_rejected(anon_client, jwt_secret):
-    """Test: Token with wrong aud → 401."""
-    token = make_token(jwt_secret, aud="wrong-app")
-    resp = await anon_client.get(
-        "/dashboard",
-        headers={"Authorization": f"Bearer {token}"}
-    )
-    assert resp.status_code == 401
-
-
-async def test_wrong_issuer_rejected(anon_client, jwt_secret):
-    """Test: Token with wrong iss → 401."""
-    token = make_token(jwt_secret, iss="https://attacker.invalid/auth/v1")
-    resp = await anon_client.get(
-        "/dashboard",
-        headers={"Authorization": f"Bearer {token}"}
-    )
-    assert resp.status_code == 401
-
-
-async def test_missing_sub_rejected(anon_client, jwt_secret):
-    """Test: Token without sub claim → 401."""
-    now = datetime.now(timezone.utc)
-    payload = {
-        "aud": "authenticated",
-        "iss": "https://test.invalid/auth/v1",
-        "exp": int((now + timedelta(hours=1)).timestamp()),
-    }
-    token = jwt.encode(payload, jwt_secret, algorithm="HS256")
-    resp = await anon_client.get(
-        "/dashboard",
-        headers={"Authorization": f"Bearer {token}"}
-    )
-    assert resp.status_code == 401
-
-
-async def test_missing_exp_rejected(anon_client, jwt_secret):
-    """Test: Token without exp claim → 401."""
-    payload = {
-        "sub": str(uuid.uuid4()),
-        "aud": "authenticated",
-        "iss": "https://test.invalid/auth/v1",
-    }
-    token = jwt.encode(payload, jwt_secret, algorithm="HS256")
-    resp = await anon_client.get(
-        "/dashboard",
-        headers={"Authorization": f"Bearer {token}"}
-    )
-    assert resp.status_code == 401
-
-
-async def test_non_uuid_sub_rejected(anon_client, jwt_secret):
-    """Test: Token with non-UUID sub → 401."""
-    token = make_token(jwt_secret, sub="not-a-uuid")
-    resp = await anon_client.get(
-        "/dashboard",
-        headers={"Authorization": f"Bearer {token}"}
-    )
-    assert resp.status_code == 401
-
-
-async def test_alg_none_rejected(anon_client):
-    """Test: Token with alg=none → 401."""
-    now = datetime.now(timezone.utc)
-    payload = {
-        "sub": str(uuid.uuid4()),
-        "aud": "authenticated",
-        "iss": "https://test.invalid/auth/v1",
-        "exp": int((now + timedelta(hours=1)).timestamp()),
-    }
-    token = jwt.encode(payload, "", algorithm="none")
-    resp = await anon_client.get(
-        "/dashboard",
-        headers={"Authorization": f"Bearer {token}"}
-    )
-    assert resp.status_code == 401
-
-
-async def test_alg_hs256_rejected(anon_client):
-    """Test: Token with HS256 (wrong algorithm) → 401."""
-    now = datetime.now(timezone.utc)
-    payload = {
-        "sub": str(uuid.uuid4()),
-        "aud": "authenticated",
-        "iss": "https://test.invalid/auth/v1",
-        "exp": int((now + timedelta(hours=1)).timestamp()),
-    }
-    token = jwt.encode(payload, "secret", algorithm="HS256")
-    resp = await anon_client.get(
-        "/dashboard",
-        headers={"Authorization": f"Bearer {token}"}
-    )
-    assert resp.status_code == 401
-
-
-# ────────────────────────────────────────────────────────────────────────────
-# Malformed and missing headers
-# ────────────────────────────────────────────────────────────────────────────
-
-
-async def test_missing_authorization_header(anon_client):
-    """Test: Request without Authorization header → 401."""
-    resp = await anon_client.get("/dashboard")
-    assert resp.status_code == 401
-
-
-async def test_malformed_authorization_header(anon_client):
-    """Test: Malformed Authorization header (not Bearer format) → 401."""
-    resp = await anon_client.get(
-        "/dashboard",
-        headers={"Authorization": "NotBearer token"}
-    )
-    assert resp.status_code == 401
-
-
-async def test_empty_authorization_header(anon_client):
-    """Test: Empty Authorization header → 401."""
-    resp = await anon_client.get(
-        "/dashboard",
-        headers={"Authorization": ""}
-    )
-    assert resp.status_code == 401
diff --git a/backend/tests/integration/test_onboarding.py b/backend/tests/integration/test_onboarding.py
index 454927e..472aac9 100644
--- a/backend/tests/integration/test_onboarding.py
+++ b/backend/tests/integration/test_onboarding.py
@@ -8,24 +8,38 @@ pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
 # Fresh user for onboarding tests — distinct from USER_A/B/C/D
 USER_ONBOARD = uuid.UUID("ee000000-0000-0000-0000-0000000000ee")
 
 @pytest.fixture
 async def onboarding_seed(admin_engine):
-    """Ensure USER_ONBOARD is wiped before/after."""
+    """Fresh user, no assets, onboarding not yet completed.
+
+    Inserts a `users` row rather than leaving none — under the single-user
+    custom-auth model (architecture-002 Phase 2) a `users` row always exists
+    before any authenticated request is reachable (created at first-run
+    bootstrap; login itself queries this table). Leaving it absent models a
+    state that can no longer occur in production.
+    """
     async with admin_engine.begin() as conn:
         await conn.execute(sa.text("DELETE FROM assets WHERE user_id = :uid"), {"uid": str(USER_ONBOARD)})
         await conn.execute(sa.text("DELETE FROM users WHERE id = :uid"), {"uid": str(USER_ONBOARD)})
+        await conn.execute(
+            sa.text(
+                "INSERT INTO users (id, email, password_hash, onboarding_completed) "
+                "VALUES (:uid, 'onboarding-test@wealthsignal.test', 'not-a-real-hash', false)"
+            ),
+            {"uid": str(USER_ONBOARD)},
+        )
     yield {"user_id": USER_ONBOARD}
     async with admin_engine.begin() as conn:
         await conn.execute(sa.text("DELETE FROM assets WHERE user_id = :uid"), {"uid": str(USER_ONBOARD)})
         await conn.execute(sa.text("DELETE FROM users WHERE id = :uid"), {"uid": str(USER_ONBOARD)})
 
 async def test_onboarding_eligibility_flow(api: AsyncClient, onboarding_seed):
     user_id = onboarding_seed["user_id"]
     client = api.as_user(user_id)
 
-    # 1. New user (no assets, no user record) -> Eligible
+    # 1. New user (users row exists, no assets, onboarding not completed) -> Eligible
     resp = await client.get("/dashboard")
     assert resp.status_code == 200
     data = resp.json()
     assert data["is_onboarding_eligible"] is True
 
diff --git a/backend/tests/integration/test_rls_backstop.py b/backend/tests/integration/test_rls_backstop.py
deleted file mode 100644
index 71d3c2d..0000000
--- a/backend/tests/integration/test_rls_backstop.py
+++ /dev/null
@@ -1,37 +0,0 @@
-"""RLS backstop, exercised at the database boundary as `app_user`.
-
-Independent of any application WHERE clause: a raw app_user connection with no
-`app.current_user_id` GUC must see zero rows (fail-closed), and only its own once
-the GUC is set. This is the second line of defense the audit (M1/§11) added.
-"""
-import sqlalchemy as sa
-import pytest
-
-pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
-
-
-async def test_no_guc_returns_zero_rows(app_engine, seed):
-    async with app_engine.connect() as conn:
-        n = await conn.scalar(sa.text("SELECT count(*) FROM assets"))
-        assert n == 0  # no app.current_user_id -> NULL -> deny all
-
-
-async def test_guc_scopes_to_that_tenant(app_engine, seed):
-    user_a, user_b = seed["A"]["user"], seed["B"]["user"]
-    async with app_engine.connect() as conn:
-        await conn.execute(sa.text("SELECT set_config('app.current_user_id', :u, false)"),
-                           {"u": str(user_a)})
-        assert await conn.scalar(sa.text("SELECT count(*) FROM assets")) == 1
-        assert await conn.scalar(sa.text("SELECT user_id FROM assets")) == user_a
-
-        await conn.execute(sa.text("SELECT set_config('app.current_user_id', :u, false)"),
-                           {"u": str(user_b)})
-        assert await conn.scalar(sa.text("SELECT count(*) FROM assets")) == 1
-        assert await conn.scalar(sa.text("SELECT user_id FROM assets")) == user_b
-
-
-async def test_blank_guc_fails_closed(app_engine, seed):
-    # The pooler can leave a stale/empty GUC; NULLIF guards the ::uuid cast -> deny.
-    async with app_engine.connect() as conn:
-        await conn.execute(sa.text("SELECT set_config('app.current_user_id', '', false)"))
-        assert await conn.scalar(sa.text("SELECT count(*) FROM assets")) == 0
diff --git a/backend/tests/integration/test_tenant_isolation.py b/backend/tests/integration/test_tenant_isolation.py
index 0dd08cc..cdcec0b 100644
--- a/backend/tests/integration/test_tenant_isolation.py
+++ b/backend/tests/integration/test_tenant_isolation.py
@@ -1,10 +1,11 @@
-"""Two-tenant isolation through the real app (app_user engine + RLS active).
+"""Two-tenant isolation through the real app (app_user engine, app-layer filtering).
 
 Reproduces SECURITY-AUDIT §5 (each tenant sees only its own data) and §4 (no IDOR:
 a tenant cannot target another's asset). Identity is injected; every query runs as
-app_user with the per-request RLS GUC set by the production hook.
+app_user and is scoped by an explicit WHERE user_id clause — the sole enforcement
+mechanism since RLS was removed under architecture-002 Phase 2 (single-user model).
 """
 import pytest
 
 pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
 
diff --git a/backend/tests/unit/test_auth_verifier.py b/backend/tests/unit/test_auth_verifier.py
deleted file mode 100644
index 48f763c..0000000
--- a/backend/tests/unit/test_auth_verifier.py
+++ /dev/null
@@ -1,317 +0,0 @@
-"""AuthN verifier matrix — reproduces SECURITY-AUDIT §3 without touching Supabase.
-
-A locally-generated ES256 keypair is used to mint tokens, and the module's JWKS
-client is patched to return the matching public key, so `get_current_user_id`
-exercises the real `jwt.decode` path (alg pinning, iss/aud/exp/sub `require`,
-signature) offline and deterministically.
-"""
-import base64
-import datetime
-import json
-import time
-import uuid
-
-import jwt
-import pytest
-from cryptography.hazmat.primitives.asymmetric import ec
-from fastapi import HTTPException
-from fastapi.security import HTTPAuthorizationCredentials
-from jwt import PyJWKClientConnectionError, PyJWKClientError
-
-from app.core import auth as auth_module
-from app.core.auth import get_current_user_id
-from app.core.config import settings
-
-pytestmark = pytest.mark.unit
-UTC = datetime.timezone.utc
-VALID_SUB = "11111111-1111-1111-1111-111111111111"
-
-
-@pytest.fixture(scope="module")
-def keypair():
-    priv = ec.generate_private_key(ec.SECP256R1())
-    return priv, priv.public_key()
-
-
-@pytest.fixture(autouse=True)
-def _patch_jwks(monkeypatch, keypair):
-    _, pub = keypair
-
-    class _Key:
-        key = pub
-
-    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", lambda token: _Key())
-
-
-@pytest.fixture(autouse=True)
-def _clear_negative_cache():
-    auth_module._negative_cache.clear()
-    yield
-    auth_module._negative_cache.clear()
-
-
-def _creds(token):
-    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
-
-
-def _mint(priv, *, sub=VALID_SUB, iss=None, aud=None, exp_delta=3600, drop=(), alg="ES256", kid=None):
-    now = datetime.datetime.now(UTC)
-    claims = {
-        "sub": sub,
-        "iss": iss if iss is not None else settings.supabase_issuer,
-        "aud": aud if aud is not None else settings.supabase_jwt_audience,
-        "iat": now,
-        "exp": now + datetime.timedelta(seconds=exp_delta),
-    }
-    for key in drop:
-        claims.pop(key, None)
-    if kid is not None:
-        return jwt.encode(claims, priv, algorithm=alg, headers={"kid": kid})
-    return jwt.encode(claims, priv, algorithm=alg)
-
-
-def _expect_401(creds):
-    with pytest.raises(HTTPException) as ei:
-        get_current_user_id(credentials=creds)
-    assert ei.value.status_code == 401
-    assert ei.value.detail in ("Not authenticated", "Invalid or expired token")  # generic, no leak
-
-
-def test_valid_token_returns_sub(keypair):
-    priv, _ = keypair
-    assert get_current_user_id(credentials=_creds(_mint(priv))) == uuid.UUID(VALID_SUB)
-
-
-def test_missing_credentials_401():
-    _expect_401(None)
-
-
-def test_expired_401(keypair):
-    priv, _ = keypair
-    _expect_401(_creds(_mint(priv, exp_delta=-10)))
-
-
-def test_wrong_audience_401(keypair):
-    priv, _ = keypair
-    _expect_401(_creds(_mint(priv, aud="someone-else")))
-
-
-def test_wrong_issuer_401(keypair):
-    priv, _ = keypair
-    _expect_401(_creds(_mint(priv, iss="https://evil.invalid/auth/v1")))
-
-
-def test_missing_sub_401(keypair):
-    priv, _ = keypair
-    _expect_401(_creds(_mint(priv, drop=("sub",))))
-
-
-def test_missing_exp_401(keypair):
-    priv, _ = keypair
-    _expect_401(_creds(_mint(priv, drop=("exp",))))
-
-
-def test_non_uuid_sub_401(keypair):
-    priv, _ = keypair
-    _expect_401(_creds(_mint(priv, sub="not-a-uuid")))
-
-
-def test_alg_hs256_key_confusion_401(keypair):
-    # Attacker signs HS256 with a guessed secret; the verifier pins ES256.
-    now = datetime.datetime.now(UTC)
-    claims = {
-        "sub": VALID_SUB,
-        "iss": settings.supabase_issuer,
-        "aud": settings.supabase_jwt_audience,
-        "iat": now,
-        "exp": now + datetime.timedelta(hours=1),
-    }
-    token = jwt.encode(claims, "guessed-secret-padded-to-32-bytes-min", algorithm="HS256")
-    _expect_401(_creds(token))
-
-
-def test_alg_none_401():
-    now = datetime.datetime.now(UTC)
-    header = {"alg": "none", "typ": "JWT"}
-    payload = {
-        "sub": VALID_SUB,
-        "iss": settings.supabase_issuer,
-        "aud": settings.supabase_jwt_audience,
-        "exp": int((now + datetime.timedelta(hours=1)).timestamp()),
-    }
-
-    def b64(d):
-        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
-
-    _expect_401(_creds(f"{b64(header)}.{b64(payload)}."))
-
-
-def test_tampered_payload_401(keypair):
-    priv, _ = keypair
-    head, payload, sig = _mint(priv).split(".")
-    payload = ("A" if payload[0] != "A" else "B") + payload[1:]
-    _expect_401(_creds(f"{head}.{payload}.{sig}"))
-
-
-def test_malformed_token_401():
-    _expect_401(_creds("not.a.valid.jwt"))
-
-
-def test_jwks_connection_failure_becomes_401_not_500(monkeypatch, keypair):
-    priv, _ = keypair
-
-    def _boom(token):
-        raise PyJWKClientConnectionError("simulated Supabase JWKS connection failure")
-
-    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _boom)
-    _expect_401(_creds(_mint(priv)))
-
-
-# ── A9: negative cache tests ─────────────────────────────────────────────────
-
-def test_unknown_kid_cached_after_first_miss(monkeypatch, keypair):
-    """Second request with the same bad kid bypasses the JWKS client entirely."""
-    priv, _ = keypair
-    token = _mint(priv, kid="bad-kid-1234")
-    call_count = 0
-
-    def _raise(t):
-        nonlocal call_count
-        call_count += 1
-        raise PyJWKClientError("no matching key")
-
-    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
-
-    _expect_401(_creds(token))
-    assert call_count == 1, "first call must reach JWKS client"
-
-    _expect_401(_creds(token))
-    assert call_count == 1, "second call must be short-circuited by negative cache"
-
-
-def test_negative_cache_hit_still_returns_401(monkeypatch, keypair):
-    """A negative cache hit is an auth rejection, not a 500."""
-    priv, _ = keypair
-    token = _mint(priv, kid="bad-kid-401-check")
-
-    def _raise(t):
-        raise PyJWKClientError("no key")
-
-    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
-    _expect_401(_creds(token))  # populate
-    _expect_401(_creds(token))  # served from cache — still 401
-
-
-def test_negative_cache_hit_emits_structured_log(monkeypatch, keypair):
-    """auth.negative_cache.hit event is logged on a cache hit."""
-    priv, _ = keypair
-    token = _mint(priv, kid="logged-kid-xyz")
-    logged: list[tuple] = []
-
-    def _raise(t):
-        raise PyJWKClientError("no key")
-
-    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
-    monkeypatch.setattr(auth_module, "log_event", lambda event, **kw: logged.append((event, kw)))
-
-    _expect_401(_creds(token))  # populate cache
-    _expect_401(_creds(token))  # cache hit → log emitted
-
-    hits = [(e, kw) for e, kw in logged if e == "auth.negative_cache.hit"]
-    assert len(hits) == 1
-    assert hits[0][1]["kid"] == "logged-k"  # truncated to 8 chars
-
-
-def test_negative_cache_log_does_not_leak_full_kid(monkeypatch, keypair):
-    """The full kid value is never written to the log."""
-    priv, _ = keypair
-    long_kid = "a" * 64
-    token = _mint(priv, kid=long_kid)
-    logged: list[tuple] = []
-
-    def _raise(t):
-        raise PyJWKClientError("no key")
-
-    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
-    monkeypatch.setattr(auth_module, "log_event", lambda event, **kw: logged.append((event, kw)))
-
-    _expect_401(_creds(token))  # populate
-    _expect_401(_creds(token))  # cache hit
-
-    for event, kw in logged:
-        if event == "auth.negative_cache.hit":
-            assert long_kid not in kw.get("kid", "")
-
-
-def test_negative_cache_entry_expires(monkeypatch, keypair):
-    """An expired negative cache entry allows the JWKS client to be called again."""
-    priv, _ = keypair
-    token = _mint(priv, kid="expiring-kid")
-    call_count = 0
-
-    def _raise(t):
-        nonlocal call_count
-        call_count += 1
-        raise PyJWKClientError("no key")
-
-    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
-
-    _expect_401(_creds(token))
-    assert call_count == 1
-
-    # Manually expire the cache entry
-    auth_module._negative_cache["expiring-kid"] = time.monotonic() - 1
-
-    _expect_401(_creds(token))  # cache miss (expired) → JWKS client called again
-    assert call_count == 2
-
-
-def test_valid_kid_not_added_to_negative_cache(keypair):
-    """Successful authentication must not populate the negative cache."""
-    priv, _ = keypair
-    token = _mint(priv, kid="valid-kid-ok")
-    result = get_current_user_id(credentials=_creds(token))
-    assert result == uuid.UUID(VALID_SUB)
-    assert "valid-kid-ok" not in auth_module._negative_cache
-
-
-def test_connection_error_does_not_populate_negative_cache(monkeypatch, keypair):
-    """A transient JWKS network failure must not blacklist a potentially valid kid."""
-    priv, _ = keypair
-    token = _mint(priv, kid="maybe-valid-kid")
-
-    def _raise(t):
-        raise PyJWKClientConnectionError("Supabase unreachable")
-
-    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
-    _expect_401(_creds(token))
-    assert "maybe-valid-kid" not in auth_module._negative_cache
-
-
-def test_empty_kid_not_cached_negatively(monkeypatch, keypair):
-    """Tokens with no kid field use kid='' which must never enter the negative cache."""
-    priv, _ = keypair
-    token = _mint(priv)  # no kid header — matches all existing test tokens
-
-    def _raise(t):
-        raise PyJWKClientError("no key")
-
-    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
-    _expect_401(_creds(token))
-    assert "" not in auth_module._negative_cache
-
-
-def test_negative_cache_maxsize_respected(monkeypatch, keypair):
-    """Cache never exceeds jwks_negative_cache_maxsize entries."""
-    for i in range(settings.jwks_negative_cache_maxsize):
-        auth_module._negative_cache[f"fill-kid-{i}"] = time.monotonic() + 60
-
-    priv, _ = keypair
-    token = _mint(priv, kid="overflow-kid")
-
-    def _raise(t):
-        raise PyJWKClientError("no key")
-
-    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
-    _expect_401(_creds(token))
-    assert len(auth_module._negative_cache) == settings.jwks_negative_cache_maxsize
diff --git a/frontend/components/AuthProvider.tsx b/frontend/components/AuthProvider.tsx
index f4d8e0a..bc84a89 100644
--- a/frontend/components/AuthProvider.tsx
+++ b/frontend/components/AuthProvider.tsx
@@ -1,40 +1,54 @@
 "use client";
 
-import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
-import type { Session, User } from "@supabase/supabase-js";
-import { supabase } from "@/lib/supabase";
+import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
+import { getMe, logout as apiLogout, refreshSession } from "@/lib/api";
 import LoginScreen from "./LoginScreen";
 
-const Ctx = createContext<{ user: User | null; signOut: () => Promise<void> }>({
-  user: null,
+const Ctx = createContext<{ userId: string | null; signOut: () => Promise<void> }>({
+  userId: null,
   signOut: async () => {},
 });
 
 export function useAuth() {
   return useContext(Ctx);
 }
 
+// Access token is short-lived (15 min server-side default) — proactively refresh
+// well within that window so an open tab never hits a hard session expiry.
+const REFRESH_INTERVAL_MS = 10 * 60 * 1000;
+
 export function AuthProvider({ children }: { children: ReactNode }) {
-  const [session, setSession] = useState<Session | null>(null);
+  const [userId, setUserId] = useState<string | null>(null);
   const [loading, setLoading] = useState(true);
+  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
+
+  async function checkSession() {
+    const me = await getMe();
+    setUserId(me?.user_id ?? null);
+  }
 
   useEffect(() => {
-    supabase.auth.getSession().then(({ data }) => {
-      setSession(data.session);
-      setLoading(false);
-    });
-    const { data: sub } = supabase.auth.onAuthStateChange((_event, s) => {
-      setSession(s);
-    });
-    return () => sub.subscription.unsubscribe();
+    checkSession().finally(() => setLoading(false));
   }, []);
 
+  useEffect(() => {
+    if (!userId) return;
+    intervalRef.current = setInterval(async () => {
+      const ok = await refreshSession();
+      if (!ok) setUserId(null);
+    }, REFRESH_INTERVAL_MS);
+    return () => {
+      if (intervalRef.current) clearInterval(intervalRef.current);
+    };
+  }, [userId]);
+
   async function signOut() {
-    await supabase.auth.signOut();
+    await apiLogout();
+    setUserId(null);
   }
 
   if (loading) return null;
-  if (!session) return <LoginScreen />;
+  if (!userId) return <LoginScreen onSuccess={checkSession} />;
 
-  return <Ctx.Provider value={{ user: session.user, signOut }}>{children}</Ctx.Provider>;
+  return <Ctx.Provider value={{ userId, signOut }}>{children}</Ctx.Provider>;
 }
diff --git a/frontend/components/LoginScreen.tsx b/frontend/components/LoginScreen.tsx
index a92b5db..9f9c67c 100644
--- a/frontend/components/LoginScreen.tsx
+++ b/frontend/components/LoginScreen.tsx
@@ -1,47 +1,23 @@
 "use client";
 
 import { useState, type FormEvent } from "react";
-import { supabase } from "@/lib/supabase";
+import { login } from "@/lib/api";
 
-type Mode = "signin" | "signup";
-
-export default function LoginScreen() {
-  const [mode, setMode] = useState<Mode>("signin");
+export default function LoginScreen({ onSuccess }: { onSuccess: () => void | Promise<void> }) {
   const [email, setEmail] = useState("");
   const [password, setPassword] = useState("");
   const [error, setError] = useState<string | null>(null);
-  const [info, setInfo] = useState<string | null>(null);
   const [busy, setBusy] = useState(false);
 
-  async function googleSignIn() {
-    setError(null);
-    const { error } = await supabase.auth.signInWithOAuth({
-      provider: "google",
-      options: { redirectTo: window.location.origin },
-    });
-    if (error) setError(error.message);
-  }
-
   async function emailSubmit(e: FormEvent) {
     e.preventDefault();
     setBusy(true);
     setError(null);
-    setInfo(null);
     try {
-      if (mode === "signin") {
-        const { error } = await supabase.auth.signInWithPassword({ email, password });
-        if (error) throw error;
-      } else {
-        const { data, error } = await supabase.auth.signUp({
-          email,
-          password,
-          options: { emailRedirectTo: window.location.origin },
-        });
-        if (error) throw error;
-        if (!data.session) setInfo("Check your email to confirm your account, then sign in.");
-      }
+      await login(email, password);
+      await onSuccess();
     } catch (err) {
       setError(err instanceof Error ? err.message : "Authentication failed");
     } finally {
       setBusy(false);
     }
@@ -59,38 +35,17 @@ export default function LoginScreen() {
         className="w-full max-w-sm rounded-2xl p-7"
         style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)" }}
       >
         <div className="mb-6 text-center">
           <h1 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
-            Investment Tracker
+            WealthSignal
           </h1>
           <p className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
-            {mode === "signin" ? "Sign in to your portfolio" : "Create your account"}
+            Sign in to your portfolio
           </p>
         </div>
 
-        <button
-          type="button"
-          onClick={googleSignIn}
-          className="flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition-colors"
-          style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--text-primary)" }}
-        >
-          <svg className="h-4 w-4" viewBox="0 0 24 24">
-            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1z"/>
-            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"/>
-            <path fill="#FBBC05" d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84z"/>
-            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/>
-          </svg>
-          Continue with Google
-        </button>
-
-        <div className="my-5 flex items-center gap-3">
-          <div className="h-px flex-1" style={{ background: "var(--border-subtle)" }} />
-          <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>or</span>
-          <div className="h-px flex-1" style={{ background: "var(--border-subtle)" }} />
-        </div>
-
         <form onSubmit={emailSubmit} className="space-y-3">
           <input
             type="email"
             required
             placeholder="Email"
@@ -100,44 +55,27 @@ export default function LoginScreen() {
             style={inputStyle}
           />
           <input
             type="password"
             required
-            minLength={6}
             placeholder="Password"
             value={password}
             onChange={(e) => setPassword(e.target.value)}
             className="w-full rounded-lg px-3 py-2.5 text-sm outline-none"
             style={inputStyle}
           />
 
           {error && <p className="text-xs text-red-400">{error}</p>}
-          {info && <p className="text-xs text-emerald-400">{info}</p>}
 
           <button
             type="submit"
             disabled={busy}
             className="w-full rounded-lg py-2.5 text-sm font-semibold text-white transition-opacity disabled:opacity-60"
             style={{ background: "linear-gradient(135deg,#f59e0b 0%,#fbbf24 100%)" }}
           >
-            {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Sign up"}
+            {busy ? "Please wait…" : "Sign in"}
           </button>
         </form>
-
-        <p className="mt-5 text-center text-xs" style={{ color: "var(--text-secondary)" }}>
-          {mode === "signin" ? "No account?" : "Already have an account?"}{" "}
-          <button
-            type="button"
-            onClick={() => {
-              setMode(mode === "signin" ? "signup" : "signin");
-              setError(null);
-              setInfo(null);
-            }}
-            className="font-medium text-amber-400"
-          >
-            {mode === "signin" ? "Sign up" : "Sign in"}
-          </button>
-        </p>
       </div>
     </div>
   );
 }
diff --git a/frontend/lib/api.ts b/frontend/lib/api.ts
index 9d5c7b0..60bac87 100644
--- a/frontend/lib/api.ts
+++ b/frontend/lib/api.ts
@@ -1,15 +1,21 @@
-import { supabase } from "./supabase";
-
 // Same-origin proxy: next.config.ts rewrites /api/* to the backend server-side.
 // Never default to localhost:8000 or a baked host IP — see CLAUDE.md "How the app is accessed".
 const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";
 
-async function authHeaders(): Promise<Record<string, string>> {
-  const { data } = await supabase.auth.getSession();
-  const token = data.session?.access_token;
-  return token ? { Authorization: `Bearer ${token}` } : {};
+// Session identity now lives in an httpOnly cookie set by the backend (architecture-002
+// Phase 2) — the browser attaches it automatically on same-origin requests, no header
+// needed. Only the CSRF double-submit cookie needs to be read and echoed back manually,
+// since it must be JS-readable (not httpOnly) for that to work.
+function readCookie(name: string): string | null {
+  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
+  return match ? decodeURIComponent(match[1]) : null;
+}
+
+function csrfHeaders(): Record<string, string> {
+  const token = readCookie("csrf_token");
+  return token ? { "X-CSRF-Token": token } : {};
 }
 
 // ── Types ──────────────────────────────────────────────────────────────────
 
 export type CryptoHoldingDetail = {
@@ -187,34 +193,59 @@ export type ImportConfirmResult = {
 };
 
 // ── Helpers ────────────────────────────────────────────────────────────────
 
 async function get<T>(path: string): Promise<T> {
-  const res = await fetch(`${API_BASE_URL}${path}`, {
-    cache: "no-store",
-    headers: await authHeaders(),
-  });
+  const res = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
   if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
   return res.json();
 }
 
 async function post<T>(path: string, body?: unknown): Promise<T> {
   const res = await fetch(`${API_BASE_URL}${path}`, {
     method: "POST",
     headers: {
       ...(body ? { "Content-Type": "application/json" } : {}),
-      ...(await authHeaders()),
+      ...csrfHeaders(),
     },
     body: body ? JSON.stringify(body) : undefined,
   });
   if (!res.ok) {
     const text = await res.text();
     throw new Error(`POST ${path} failed: ${res.status} ${text}`);
   }
   return res.json();
 }
 
+// ── Auth ───────────────────────────────────────────────────────────────────
+
+export async function login(email: string, password: string): Promise<void> {
+  const res = await fetch(`${API_BASE_URL}/auth/login`, {
+    method: "POST",
+    headers: { "Content-Type": "application/json" },
+    body: JSON.stringify({ email, password }),
+  });
+  if (!res.ok) {
+    const text = await res.text();
+    throw new Error(`Login failed: ${res.status} ${text}`);
+  }
+}
+
+export async function logout(): Promise<void> {
+  await fetch(`${API_BASE_URL}/auth/logout`, { method: "POST", headers: csrfHeaders() });
+}
+
+export async function getMe(): Promise<{ user_id: string } | null> {
+  const res = await fetch(`${API_BASE_URL}/auth/me`, { cache: "no-store" });
+  return res.ok ? res.json() : null;
+}
+
+export async function refreshSession(): Promise<boolean> {
+  const res = await fetch(`${API_BASE_URL}/auth/refresh`, { method: "POST", headers: csrfHeaders() });
+  return res.ok;
+}
+
 // ── API functions ──────────────────────────────────────────────────────────
 
 export const getDashboard = () => get<{
   total_value: number;
   total_invested: number;
@@ -246,14 +277,13 @@ export const getMonthlyPerformance = () => get<PerformanceResult>("/performance/
 export const getDailyPerformance = () => get<PerformanceResult>("/performance/daily");
 
 export async function importCsvDryRun(file: File): Promise<ImportDryRunResult> {
   const form = new FormData();
   form.append("file", file);
-  const headers = await authHeaders();
   const res = await fetch(`${API_BASE_URL}/import/csv?dry_run=true`, {
     method: "POST",
-    headers,
+    headers: csrfHeaders(),
     body: form,
   });
   if (!res.ok) {
     const text = await res.text();
     throw new Error(`Import preview failed: ${res.status} ${text}`);
@@ -262,14 +292,13 @@ export async function importCsvDryRun(file: File): Promise<ImportDryRunResult> {
 }
 
 export async function importCsvConfirm(file: File): Promise<ImportConfirmResult> {
   const form = new FormData();
   form.append("file", file);
-  const headers = await authHeaders();
   const res = await fetch(`${API_BASE_URL}/import/csv?dry_run=false`, {
     method: "POST",
-    headers,
+    headers: csrfHeaders(),
     body: form,
   });
   if (!res.ok) {
     const text = await res.text();
     throw new Error(`Import failed: ${res.status} ${text}`);
@@ -310,11 +339,11 @@ export async function createAsset(payload: {
 }
 
 export async function deleteAsset(assetId: string) {
   const res = await fetch(`${API_BASE_URL}/assets/${assetId}`, {
     method: "DELETE",
-    headers: await authHeaders(),
+    headers: csrfHeaders(),
   });
   if (!res.ok) {
     const text = await res.text();
     throw new Error(`DELETE /assets/${assetId} failed: ${res.status} ${text}`);
   }
@@ -341,14 +370,11 @@ export async function topUpSavings(assetId: string, amount: number) {
     { amount },
   );
 }
 
 export async function exportHoldings() {
-  const headers = await authHeaders();
-  const res = await fetch(`${API_BASE_URL}/export/holdings`, {
-    headers,
-  });
+  const res = await fetch(`${API_BASE_URL}/export/holdings`);
   if (!res.ok) throw new Error(`Export holdings failed: ${res.status}`);
   const blob = await res.blob();
   const url = window.URL.createObjectURL(blob);
   const a = document.createElement("a");
   a.href = url;
@@ -363,14 +389,11 @@ export async function exportHoldings() {
   window.URL.revokeObjectURL(url);
   document.body.removeChild(a);
 }
 
 export async function exportTransactions() {
-  const headers = await authHeaders();
-  const res = await fetch(`${API_BASE_URL}/export/transactions`, {
-    headers,
-  });
+  const res = await fetch(`${API_BASE_URL}/export/transactions`);
   if (!res.ok) throw new Error(`Export transactions failed: ${res.status}`);
   const blob = await res.blob();
   const url = window.URL.createObjectURL(blob);
   const a = document.createElement("a");
   a.href = url;
diff --git a/frontend/lib/supabase.ts b/frontend/lib/supabase.ts
deleted file mode 100644
index 77d90aa..0000000
--- a/frontend/lib/supabase.ts
+++ /dev/null
@@ -1,13 +0,0 @@
-import { createClient } from "@supabase/supabase-js";
-
-const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
-const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
-
-export const supabase = createClient(url, anonKey, {
-  auth: {
-    persistSession: true,
-    autoRefreshToken: true,
-    detectSessionInUrl: true,
-    flowType: "pkce",
-  },
-});
diff --git a/frontend/package-lock.json b/frontend/package-lock.json
index b6add75..b037f9c 100644
--- a/frontend/package-lock.json
+++ b/frontend/package-lock.json
@@ -6,11 +6,10 @@
   "packages": {
     "": {
       "name": "frontend",
       "version": "0.1.0",
       "dependencies": {
-        "@supabase/supabase-js": "^2.107.0",
         "lucide-react": "^1.16.0",
         "next": "16.2.6",
         "react": "19.2.4",
         "react-dom": "19.2.4",
         "recharts": "^3.8.1"
@@ -1302,94 +1301,10 @@
       "version": "0.3.0",
       "resolved": "https://registry.npmjs.org/@standard-schema/utils/-/utils-0.3.0.tgz",
       "integrity": "sha512-e7Mew686owMaPJVNNLs55PUvgz371nKgwsc4vxE49zsODpJEnxgxRo2y/OKrqueavXgZNMDVj3DdHFlaSAeU8g==",
       "license": "MIT"
     },
-    "node_modules/@supabase/auth-js": {
-      "version": "2.107.0",
-      "resolved": "https://registry.npmjs.org/@supabase/auth-js/-/auth-js-2.107.0.tgz",
-      "integrity": "sha512-XA7x+WIeIvuC3GTZ2ey67QcBbGw4n+o5B7M+dMm9KT1lL3wX1B52DfEWW00WuPt/LnniJLLIn1WIm9YPtuxzKQ==",
-      "license": "MIT",
-      "dependencies": {
-        "tslib": "2.8.1"
-      },
-      "engines": {
-        "node": ">=20.0.0"
-      }
-    },
-    "node_modules/@supabase/functions-js": {
-      "version": "2.107.0",
-      "resolved": "https://registry.npmjs.org/@supabase/functions-js/-/functions-js-2.107.0.tgz",
-      "integrity": "sha512-iMtRUmEj1KOgQd/a3MR4hnBlPnZc62DW8+z8aPpnzbxWkexEZUVL2fSgvvp15gqFg1V55e2yMGqgK+yhSQxp5w==",
-      "license": "MIT",
-      "dependencies": {
-        "tslib": "2.8.1"
-      },
-      "engines": {
-        "node": ">=20.0.0"
-      }
-    },
-    "node_modules/@supabase/phoenix": {
-      "version": "0.4.2",
-      "resolved": "https://registry.npmjs.org/@supabase/phoenix/-/phoenix-0.4.2.tgz",
-      "integrity": "sha512-YSAGnmDAfuleFCVt3CeurQZAhxRfXWeZIIkwp7NhYzQ1UwW6ePSnzsFAiUm/mbCkfoCf70QQHKW/K6RKh52a4A==",
-      "license": "MIT"
-    },
-    "node_modules/@supabase/postgrest-js": {
-      "version": "2.107.0",
-      "resolved": "https://registry.npmjs.org/@supabase/postgrest-js/-/postgrest-js-2.107.0.tgz",
-      "integrity": "sha512-7ARs47/tyIjX7T0Ive20d4NY8zQYXsP5/P07jJWxffSIM2gpnSnGRnL/Fe15GPbdjsW2sTYeckHcyaoKbM6yWQ==",
-      "license": "MIT",
-      "dependencies": {
-        "tslib": "2.8.1"
-      },
-      "engines": {
-        "node": ">=20.0.0"
-      }
-    },
-    "node_modules/@supabase/realtime-js": {
-      "version": "2.107.0",
-      "resolved": "https://registry.npmjs.org/@supabase/realtime-js/-/realtime-js-2.107.0.tgz",
-      "integrity": "sha512-cF2KYdR3JIn9YlWGeluY9S0G+otqTdL6hB8GzpatlEIY6fZudCcyFo6Dc3+X9tjeb+x9XcIyNAk9qhNAknjH1A==",
-      "license": "MIT",
-      "dependencies": {
-        "@supabase/phoenix": "^0.4.2",
-        "tslib": "2.8.1"
-      },
-      "engines": {
-        "node": ">=20.0.0"
-      }
-    },
-    "node_modules/@supabase/storage-js": {
-      "version": "2.107.0",
-      "resolved": "https://registry.npmjs.org/@supabase/storage-js/-/storage-js-2.107.0.tgz",
-      "integrity": "sha512-/X8OOVwKBn8aVKuHAGOz2yLA0d2OauqhVuy4mNtN+o7wttHOgx1/j+pqOzlsjmhOHrYykF6AJNZhs3gKZzcMUw==",
-      "license": "MIT",
-      "dependencies": {
-        "iceberg-js": "^0.8.1",
-        "tslib": "2.8.1"
-      },
-      "engines": {
-        "node": ">=20.0.0"
-      }
-    },
-    "node_modules/@supabase/supabase-js": {
-      "version": "2.107.0",
-      "resolved": "https://registry.npmjs.org/@supabase/supabase-js/-/supabase-js-2.107.0.tgz",
-      "integrity": "sha512-ChKzdlWVweMUUhr0U79JhMmgm1haS/C5JquaiCDr70JaGARRtjjoY9rkIheXWybXxTSNzRiQs3Sk8IAg1HS3ZA==",
-      "license": "MIT",
-      "dependencies": {
-        "@supabase/auth-js": "2.107.0",
-        "@supabase/functions-js": "2.107.0",
-        "@supabase/postgrest-js": "2.107.0",
-        "@supabase/realtime-js": "2.107.0",
-        "@supabase/storage-js": "2.107.0"
-      },
-      "engines": {
-        "node": ">=20.0.0"
-      }
-    },
     "node_modules/@swc/helpers": {
       "version": "0.5.15",
       "resolved": "https://registry.npmjs.org/@swc/helpers/-/helpers-0.5.15.tgz",
       "integrity": "sha512-JQ5TuMi45Owi4/BIMAJBoSQoOJu12oOk/gADqlcUL9JEdHB8vyjUSsxqeNXnmXHjYKMi2WcYtezGEEhqUI/E2g==",
       "license": "Apache-2.0",
@@ -4319,19 +4234,10 @@
       "license": "MIT",
       "dependencies": {
         "hermes-estree": "0.25.1"
       }
     },
-    "node_modules/iceberg-js": {
-      "version": "0.8.1",
-      "resolved": "https://registry.npmjs.org/iceberg-js/-/iceberg-js-0.8.1.tgz",
-      "integrity": "sha512-1dhVQZXhcHje7798IVM+xoo/1ZdVfzOMIc8/rgVSijRK38EDqOJoGula9N/8ZI5RD8QTxNQtK/Gozpr+qUqRRA==",
-      "license": "MIT",
-      "engines": {
-        "node": ">=20.0.0"
-      }
-    },
     "node_modules/ignore": {
       "version": "5.3.2",
       "resolved": "https://registry.npmjs.org/ignore/-/ignore-5.3.2.tgz",
       "integrity": "sha512-hsBTNUqQTDwkWtcdYI2i06Y/nUBEsNEDJKjWdigLvegy8kDuJAS8uRlpkkcQpyEXL0Z/pjDy5HBmMjRCJ2gq+g==",
       "dev": true,
diff --git a/frontend/package.json b/frontend/package.json
index cb50075..ce81489 100644
--- a/frontend/package.json
+++ b/frontend/package.json
@@ -7,11 +7,10 @@
     "build": "next build",
     "start": "next start",
     "lint": "eslint"
   },
   "dependencies": {
-    "@supabase/supabase-js": "^2.107.0",
     "lucide-react": "^1.16.0",
     "next": "16.2.6",
     "react": "19.2.4",
     "react-dom": "19.2.4",
     "recharts": "^3.8.1"
```

## New File: backend/alembic/versions/b3f1a9c7d2e4_custom_auth_password_refresh_tokens_.py

```
"""custom auth: password_hash, refresh_tokens, drop RLS

architecture-002 Phase 2 — replacing Supabase Auth with self-issued bcrypt+JWT.
Single-user model: the multi-tenant RLS backstop (6a8bdc1bb742, a1b2c3d4e5f6) is
removed entirely rather than kept dormant. App-layer WHERE-user_id filtering,
already documented as mandatory, is unchanged and remains the sole enforcement.

Revision ID: b3f1a9c7d2e4
Revises: 62c0aa1dd7cf
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'b3f1a9c7d2e4'
down_revision: Union[str, Sequence[str], None] = '62c0aa1dd7cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Every table RLS was ever enabled on, across all three migrations that added
# policies over time: 6a8bdc1bb742 (original 8), a1b2c3d4e5f6 (users, added
# separately), a6c964d55107 (manual_holdings, added later still — easy to miss).
_RLS_TABLES = (
    "users",
    "assets",
    "transactions",
    "valuation_history",
    "portfolio_snapshots",
    "ai_insights",
    "crypto_holdings",
    "fixed_income_holdings",
    "mutual_fund_holdings",
    "manual_holdings",
)


def upgrade() -> None:
    # email lived entirely in Supabase's own auth.users before this — this table
    # only ever stored the onboarding flag keyed by the Supabase-issued UUID.
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(), nullable=False, server_default=""),
    )
    # server_default was only to satisfy NOT NULL against a (possibly non-empty)
    # existing table; drop it so future inserts must supply a real hash explicitly.
    op.alter_column("users", "password_hash", server_default=None)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    for t in _RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")
        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    _USING_USERS = "id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"
    _USING_OTHERS = "user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"

    for t in _RLS_TABLES:
        using = _USING_USERS if t == "users" else _USING_OTHERS
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {t} FOR ALL "
            f"USING ({using}) WITH CHECK ({using})"
        )

    op.drop_table("refresh_tokens")
    op.drop_column("users", "password_hash")

```

## New File: backend/app/api/auth.py

```
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import (
    clear_auth_cookies,
    create_access_token,
    generate_csrf_token,
    generate_refresh_token,
    get_current_user_id,
    hash_password,
    hash_refresh_token,
    set_auth_cookies,
    verify_password,
)
from app.core.config import settings
from app.core.observability import log_event
from app.core.ratelimit import client_ip, limiter
from app.db.models import RefreshToken, User
from app.db.session import AdminSessionLocal

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


async def bootstrap_admin_user() -> None:
    """First-run only: create the single admin user if `users` is empty.

    Idempotency guard: checks for ANY existing row, not just a matching email —
    without this, a container restart would silently re-run and could be mistaken
    for a password reset. Once a user exists, this is a permanent no-op.
    """
    async with AdminSessionLocal() as session:
        existing = (await session.execute(select(User.id).limit(1))).first()
        if existing is not None:
            return
        user = User(
            id=uuid.uuid4(),
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            onboarding_completed=False,
        )
        session.add(user)
        await session.commit()
        log_event("auth.bootstrap.created_admin", email=settings.admin_email)


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    ip = client_ip(request)
    allowed, retry = limiter.check(f"login:{ip}", settings.rl_login_attempts)
    if not allowed:
        log_event("auth.login.rate_limited", ip=ip)
        raise HTTPException(
            status_code=429, detail="Too many login attempts",
            headers={"Retry-After": str(retry)},
        )

    async with AdminSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.email == payload.email))
        ).scalar_one_or_none()

        # Constant-shape failure: run verify_password even on a missing user
        # (against a dummy hash) so a bad email isn't distinguishable by timing
        # from a bad password.
        password_hash = user.password_hash if user else "$2b$12$" + "0" * 53
        valid = verify_password(payload.password, password_hash)
        if not user or not valid:
            log_event("auth.login.failed", ip=ip)
            raise HTTPException(status_code=401, detail="Invalid email or password")

        access_token = create_access_token(user.id)
        raw_refresh, refresh_hash, expires_at = generate_refresh_token()
        session.add(RefreshToken(
            id=uuid.uuid4(), user_id=user.id, token_hash=refresh_hash, expires_at=expires_at,
        ))
        await session.commit()

    set_auth_cookies(
        response, access_token=access_token, refresh_token=raw_refresh,
        csrf_token=generate_csrf_token(),
    )
    log_event("auth.login.success", user=str(user.id))
    return {"user_id": str(user.id)}


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
):
    if refresh_token:
        token_hash = hash_refresh_token(refresh_token)
        async with AdminSessionLocal() as session:
            row = (
                await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
            ).scalar_one_or_none()
            if row and row.revoked_at is None:
                row.revoked_at = datetime.now(timezone.utc)
                await session.commit()
    clear_auth_cookies(response)
    return {"logged_out": True}


@router.post("/refresh")
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_hash = hash_refresh_token(refresh_token)
    async with AdminSessionLocal() as session:
        row = (
            await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        ).scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if row is None or row.revoked_at is not None or row.expires_at < now:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        # Rotate: revoke the used token, issue a fresh one. Lets reuse of a stolen
        # or already-consumed refresh token be detected (its hash no longer exists
        # as an active row) instead of remaining valid indefinitely.
        row.revoked_at = now
        row.last_used_at = now
        raw_refresh, refresh_hash, expires_at = generate_refresh_token()
        session.add(RefreshToken(
            id=uuid.uuid4(), user_id=row.user_id, token_hash=refresh_hash, expires_at=expires_at,
        ))
        await session.commit()
        user_id = row.user_id

    access_token = create_access_token(user_id)
    set_auth_cookies(
        response, access_token=access_token, refresh_token=raw_refresh,
        csrf_token=generate_csrf_token(),
    )
    return {"user_id": str(user_id)}


@router.get("/me")
async def me(user_id: uuid.UUID = Depends(get_current_user_id)):
    return {"user_id": str(user_id)}

```

## New File: backend/tests/integration/test_auth_endpoints.py

```
"""Custom auth (architecture-002 Phase 2) — end-to-end through real HTTP endpoints
against a real Postgres container. Replaces the deleted Supabase-JWT test_auth_jwt.py.

Covers ROADMAP.md step 5's required completion set: login, token expiry/refresh,
revocation, bootstrap, ownership checks (via test_auth_isolation.py, unchanged),
plus CSRF and a negative test proving the old Supabase auth path is actually gone.
"""
import uuid

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

ADMIN_EMAIL = "founder@wealthsignal.test"
ADMIN_PASSWORD = "correct-horse-battery-staple-9000"


@pytest.fixture
async def super_engine(pg):
    eng = create_async_engine(pg["super_url"], connect_args={})
    yield eng
    await eng.dispose()


@pytest.fixture(autouse=True)
async def _clean_auth_state(super_engine):
    """users/refresh_tokens aren't touched by the shared `seed` fixture's truncate
    list — clean them explicitly so bootstrap and login tests are independent."""
    async with super_engine.begin() as conn:
        await conn.execute(sa.text("TRUNCATE refresh_tokens, users CASCADE"))
    from app.core.ratelimit import limiter
    limiter.clear()  # shared in-process state; don't let one test's attempts count against another
    yield


@pytest.fixture
async def auth_client(super_engine, monkeypatch):
    import app.api.auth as auth_api
    from app.main import app

    monkeypatch.setattr(auth_api, "AdminSessionLocal", async_sessionmaker(super_engine, expire_on_commit=False))
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def bootstrapped(auth_client, monkeypatch):
    """A single admin user exists, matching ADMIN_EMAIL/ADMIN_PASSWORD."""
    monkeypatch.setattr("app.core.config.settings.admin_email", ADMIN_EMAIL)
    monkeypatch.setattr("app.core.config.settings.admin_password", ADMIN_PASSWORD)
    import app.api.auth as auth_api
    await auth_api.bootstrap_admin_user()
    return auth_client


# ── Bootstrap ────────────────────────────────────────────────────────────────

async def test_bootstrap_creates_single_admin_user(super_engine, auth_client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.admin_email", ADMIN_EMAIL)
    monkeypatch.setattr("app.core.config.settings.admin_password", ADMIN_PASSWORD)
    import app.api.auth as auth_api

    await auth_api.bootstrap_admin_user()
    async with super_engine.connect() as conn:
        count = await conn.scalar(sa.text("SELECT count(*) FROM users"))
        email = await conn.scalar(sa.text("SELECT email FROM users LIMIT 1"))
    assert count == 1
    assert email == ADMIN_EMAIL


async def test_bootstrap_is_idempotent(super_engine, auth_client, monkeypatch):
    """A container restart re-running bootstrap must not reset the password —
    the guard is 'any user exists', not 'this email exists'."""
    monkeypatch.setattr("app.core.config.settings.admin_email", ADMIN_EMAIL)
    monkeypatch.setattr("app.core.config.settings.admin_password", ADMIN_PASSWORD)
    import app.api.auth as auth_api

    await auth_api.bootstrap_admin_user()
    async with super_engine.connect() as conn:
        hash_after_first = await conn.scalar(sa.text("SELECT password_hash FROM users LIMIT 1"))

    # Simulate a restart with a different password in env — must NOT overwrite.
    monkeypatch.setattr("app.core.config.settings.admin_password", "a-totally-different-password")
    await auth_api.bootstrap_admin_user()
    async with super_engine.connect() as conn:
        count = await conn.scalar(sa.text("SELECT count(*) FROM users"))
        hash_after_second = await conn.scalar(sa.text("SELECT password_hash FROM users LIMIT 1"))

    assert count == 1
    assert hash_after_second == hash_after_first


# ── Login ────────────────────────────────────────────────────────────────────

async def test_login_with_correct_credentials_succeeds(bootstrapped):
    resp = await bootstrapped.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies
    assert "csrf_token" in resp.cookies


async def test_login_with_wrong_password_rejected(bootstrapped):
    resp = await bootstrapped.post("/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert resp.status_code == 401
    assert "access_token" not in resp.cookies


async def test_login_with_unknown_email_rejected(bootstrapped):
    resp = await bootstrapped.post("/auth/login", json={"email": "nobody@test.invalid", "password": "x"})
    assert resp.status_code == 401


async def test_login_rate_limited_after_repeated_failures(bootstrapped):
    from app.core.config import settings
    for _ in range(settings.rl_login_attempts):
        await bootstrapped.post("/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    resp = await bootstrapped.post("/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert resp.status_code == 429


async def test_me_requires_valid_session(bootstrapped):
    resp = await bootstrapped.get("/auth/me")
    assert resp.status_code == 401

    login = await bootstrapped.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert login.status_code == 200
    resp = await bootstrapped.get("/auth/me")
    assert resp.status_code == 200


# ── Refresh (rotation) ───────────────────────────────────────────────────────

async def test_refresh_issues_new_tokens_and_rotates(bootstrapped):
    login = await bootstrapped.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    old_refresh = login.cookies["refresh_token"]

    resp = await bootstrapped.post("/auth/refresh", headers={"X-CSRF-Token": login.cookies["csrf_token"]})
    assert resp.status_code == 200
    new_refresh = resp.cookies["refresh_token"]
    assert new_refresh != old_refresh

    # Old refresh token must no longer work (rotated = revoked on use).
    bootstrapped.cookies.set("refresh_token", old_refresh)
    resp2 = await bootstrapped.post("/auth/refresh", headers={"X-CSRF-Token": resp.cookies["csrf_token"]})
    assert resp2.status_code == 401


async def test_refresh_without_cookie_rejected(bootstrapped):
    # No refresh_token cookie, but a matching CSRF pair — isolates the "no
    # session" 401 path from the CSRF 403 path (covered separately below).
    bootstrapped.cookies.set("csrf_token", "manual-csrf-value")
    resp = await bootstrapped.post("/auth/refresh", headers={"X-CSRF-Token": "manual-csrf-value"})
    assert resp.status_code == 401


# ── Logout / revocation ──────────────────────────────────────────────────────

async def test_logout_revokes_refresh_token(bootstrapped):
    login = await bootstrapped.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    csrf = login.cookies["csrf_token"]
    old_refresh = login.cookies["refresh_token"]

    logout = await bootstrapped.post("/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 200

    # logout clears the csrf cookie too — set a fresh matching pair manually so
    # this request tests revocation, not an incidental CSRF mismatch.
    bootstrapped.cookies.set("csrf_token", "manual-csrf-value")
    bootstrapped.cookies.set("refresh_token", old_refresh, path="/auth")
    resp = await bootstrapped.post("/auth/refresh", headers={"X-CSRF-Token": "manual-csrf-value"})
    assert resp.status_code == 401


# ── CSRF (double-submit) ─────────────────────────────────────────────────────

async def test_mutating_request_without_csrf_header_rejected(bootstrapped):
    await bootstrapped.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    resp = await bootstrapped.post("/auth/logout")  # no X-CSRF-Token header
    assert resp.status_code == 403


async def test_mutating_request_with_wrong_csrf_header_rejected(bootstrapped):
    await bootstrapped.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    resp = await bootstrapped.post("/auth/logout", headers={"X-CSRF-Token": "not-the-right-value"})
    assert resp.status_code == 403


async def test_login_itself_is_csrf_exempt(bootstrapped):
    # No prior session/csrf cookie exists yet — login must still be reachable.
    resp = await bootstrapped.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200


# ── Old auth path is actually gone ───────────────────────────────────────────

async def test_old_style_bearer_token_no_longer_accepted(bootstrapped):
    """Cookie-based auth replaced the Authorization-header path entirely — a
    request carrying only a Bearer token (the old Supabase pattern) must be
    treated as unauthenticated, not silently accepted."""
    login = await bootstrapped.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    access_token = login.cookies["access_token"]
    bootstrapped.cookies.clear()
    resp = await bootstrapped.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 401

```

## New File: backend/tests/unit/test_auth.py

```
"""Custom auth unit tests (architecture-002 Phase 2) — bcrypt hashing, HS256
access-token verification, CSRF double-submit check. Replaces the old Supabase
JWKS-based test_auth_verifier.py (deleted — that verifier no longer exists)."""
import datetime
import uuid

import jwt
import pytest
from fastapi import HTTPException

from app.core import auth as auth_module
from app.core.auth import (
    create_access_token,
    csrf_check,
    generate_refresh_token,
    get_current_user_id,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.core.config import settings

pytestmark = pytest.mark.unit
UTC = datetime.timezone.utc
VALID_SUB = uuid.UUID("11111111-1111-1111-1111-111111111111")


# ── Password hashing ─────────────────────────────────────────────────────────

def test_hash_and_verify_round_trip():
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h)


def test_verify_rejects_wrong_password():
    h = hash_password("correct horse battery staple")
    assert not verify_password("wrong password", h)


def test_hash_is_not_the_plaintext():
    h = hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"


def test_verify_malformed_hash_fails_closed():
    assert not verify_password("anything", "not-a-real-bcrypt-hash")


# ── Access token (HS256) ──────────────────────────────────────────────────────

def _expect_401(token):
    with pytest.raises(HTTPException) as ei:
        get_current_user_id(access_token=token)
    assert ei.value.status_code == 401


def test_valid_access_token_returns_sub():
    token = create_access_token(VALID_SUB)
    assert get_current_user_id(access_token=token) == VALID_SUB


def test_missing_cookie_401():
    _expect_401(None)


def test_expired_token_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": str(VALID_SUB), "iat": now, "exp": now - datetime.timedelta(seconds=1)}
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    _expect_401(token)


def test_missing_sub_401():
    now = datetime.datetime.now(UTC)
    claims = {"iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    _expect_401(token)


def test_non_uuid_sub_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": "not-a-uuid", "iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    _expect_401(token)


def test_wrong_secret_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": str(VALID_SUB), "iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, "a-completely-different-secret", algorithm="HS256")
    _expect_401(token)


def test_alg_none_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": str(VALID_SUB), "iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, "", algorithm="none")
    _expect_401(token)


def test_tampered_payload_401():
    token = create_access_token(VALID_SUB)
    head, payload, sig = token.split(".")
    payload = ("A" if payload[0] != "A" else "B") + payload[1:]
    _expect_401(f"{head}.{payload}.{sig}")


def test_malformed_token_401():
    _expect_401("not.a.valid.jwt")


def test_old_supabase_style_es256_token_rejected():
    """A token from the old Supabase Auth path (ES256, different issuer/audience
    shape) must not be accepted post-cutover — proves the old path is gone, not
    just that a new one was added alongside it."""
    from cryptography.hazmat.primitives.asymmetric import ec

    priv = ec.generate_private_key(ec.SECP256R1())
    now = datetime.datetime.now(UTC)
    claims = {
        "sub": str(VALID_SUB),
        "iss": "https://old-project.supabase.co/auth/v1",
        "aud": "authenticated",
        "iat": now,
        "exp": now + datetime.timedelta(hours=1),
    }
    token = jwt.encode(claims, priv, algorithm="ES256")
    _expect_401(token)


# ── Refresh token ──────────────────────────────────────────────────────────

def test_refresh_token_hash_is_deterministic():
    raw, token_hash, expires_at = generate_refresh_token()
    assert hash_refresh_token(raw) == token_hash


def test_refresh_token_hash_not_the_raw_value():
    raw, token_hash, _ = generate_refresh_token()
    assert token_hash != raw


def test_refresh_token_expiry_in_future():
    _, _, expires_at = generate_refresh_token()
    assert expires_at > datetime.datetime.now(UTC)


# ── CSRF double-submit ──────────────────────────────────────────────────────
# CSRF only applies to sessions (has_session=True) — an anonymous request has no
# ambient authority to hijack and falls through to the normal 401 auth gate.

def test_csrf_get_request_exempt():
    csrf_check("GET", "/assets", True, None, None)  # no raise


def test_csrf_login_path_exempt():
    csrf_check("POST", "/auth/login", True, None, None)  # no raise


def test_csrf_no_session_exempt():
    # No access_token cookie -> downstream auth gate handles it (401), not CSRF.
    csrf_check("POST", "/assets", False, None, None)  # no raise


def test_csrf_missing_cookie_rejected():
    with pytest.raises(HTTPException) as ei:
        csrf_check("POST", "/assets", True, None, "some-header-value")
    assert ei.value.status_code == 403


def test_csrf_missing_header_rejected():
    with pytest.raises(HTTPException) as ei:
        csrf_check("POST", "/assets", True, "some-cookie-value", None)
    assert ei.value.status_code == 403


def test_csrf_mismatched_values_rejected():
    with pytest.raises(HTTPException) as ei:
        csrf_check("POST", "/assets", True, "cookie-value", "different-header-value")
    assert ei.value.status_code == 403


def test_csrf_matching_values_accepted():
    csrf_check("POST", "/assets", True, "matching-value", "matching-value")  # no raise

```
