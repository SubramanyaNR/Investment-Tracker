import hashlib
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Cookie, HTTPException

from app.core.config import settings
from app.core.observability import log_event

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"


# ── Password hashing ──────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash (shouldn't happen outside a corrupted DB row) — fail closed.
        return False


# ── Access token (short-lived JWT, HS256) ─────────────────────────────────

def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=settings.access_token_ttl_seconds),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


_disabled_mode_admin_id: uuid.UUID | None = None


async def _resolve_disabled_mode_user_id() -> uuid.UUID:
    """AUTH_ENABLED=false: every request resolves to the single bootstrapped
    admin user — never null, never client-supplied. Cached after the first
    lookup since there is exactly one user row for the life of a single-user
    deployment; avoids a DB round trip on every request."""
    global _disabled_mode_admin_id
    if _disabled_mode_admin_id is not None:
        return _disabled_mode_admin_id

    # Local imports: core/auth.py otherwise has no DB dependency, and this path
    # only ever runs when auth is disabled.
    from sqlalchemy import select
    from app.db.models import User
    from app.db.session import AdminSessionLocal

    async with AdminSessionLocal() as session:
        row = (await session.execute(select(User.id).limit(1))).first()
    if row is None:
        raise HTTPException(status_code=500, detail="Auth is disabled but no admin user exists yet")
    _disabled_mode_admin_id = row[0]
    return _disabled_mode_admin_id


async def get_current_user_id(access_token: str | None = Cookie(default=None)) -> uuid.UUID:
    if not settings.auth_enabled:
        return await _resolve_disabled_mode_user_id()
    if access_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        claims = jwt.decode(
            access_token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        return uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Refresh token (opaque random value; only its SHA-256 hash is stored) ──
# High-entropy random token, not a low-entropy password — a fast deterministic
# hash (for direct DB lookup by hash) is the correct tool here, not bcrypt.

def generate_refresh_token() -> tuple[str, str, datetime]:
    """Returns (raw_token, token_hash, expires_at). Raw token goes in the cookie;
    only the hash is ever persisted."""
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.refresh_token_ttl_seconds)
    return raw, token_hash, expires_at


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


# ── CSRF (double-submit cookie) ────────────────────────────────────────────

def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# No session exists yet when logging in, so there's nothing to double-submit against.
_CSRF_EXEMPT_PATHS = {"/auth/login"}


def csrf_check(
    method: str, path: str, has_session: bool, cookie_value: str | None, header_value: str | None,
) -> None:
    """CSRF only matters when there's a session to ride on — an anonymous request
    has no ambient authority to hijack, so it falls through to the normal 401 auth
    gate instead of being intercepted here."""
    if method not in _UNSAFE_METHODS or path in _CSRF_EXEMPT_PATHS or not has_session:
        return
    if not cookie_value or not header_value or not secrets.compare_digest(cookie_value, header_value):
        log_event("auth.csrf.reject", path=path)
        raise HTTPException(status_code=403, detail="CSRF check failed")


# ── Cookie helpers ─────────────────────────────────────────────────────────

def set_auth_cookies(response, *, access_token: str, refresh_token: str, csrf_token: str) -> None:
    response.set_cookie(
        ACCESS_COOKIE, access_token, max_age=settings.access_token_ttl_seconds,
        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh_token, max_age=settings.refresh_token_ttl_seconds,
        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/auth",
    )
    response.set_cookie(
        CSRF_COOKIE, csrf_token, max_age=settings.access_token_ttl_seconds,
        httponly=False, secure=settings.cookie_secure, samesite="lax", path="/",
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/auth")
    response.delete_cookie(CSRF_COOKIE, path="/")
