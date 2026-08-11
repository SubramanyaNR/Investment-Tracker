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
