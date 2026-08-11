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
