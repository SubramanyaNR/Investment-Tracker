"""In-process fixed-window rate limiting, exposed as FastAPI dependencies.

Per-user limits (keyed on the JWT `sub`) are reliable regardless of the proxy.
Per-IP limits (for public /market/*) read a trusted X-Forwarded-For — the backend
binds 127.0.0.1 (reachable only via the proxy), so a proxy-set XFF is trustworthy;
nginx (B1) makes the real client IP fully accurate. Single process, so counters are
globally consistent; swap for Redis only when running multiple workers/instances.
"""
import time
import uuid
from typing import Callable

from fastapi import Depends, HTTPException, Request

from app.core.auth import get_current_user_id
from app.core.config import settings
from app.core.observability import log_event

WINDOW = 60  # seconds


class FixedWindowLimiter:
    def __init__(self):
        self._hits: dict[str, tuple[float, int]] = {}  # key -> (window_start, count)

    def check(self, key: str, limit: int, window: int = WINDOW, now: float | None = None):
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic() if now is None else now
        start, count = self._hits.get(key, (now, 0))
        if now - start >= window:
            start, count = now, 0
        count += 1
        self._hits[key] = (start, count)
        if count > limit:
            return False, int(window - (now - start)) + 1
        return True, 0

    def clear(self) -> None:
        self._hits.clear()


limiter = FixedWindowLimiter()


def client_ip(request: Request) -> str:
    if settings.trust_forwarded_for:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _enforce(key: str, limit: int, *, scope: str, route: str, who: str) -> None:
    allowed, retry = limiter.check(key, limit)
    if not allowed:
        log_event("ratelimit.block", scope=scope, route=route, key=who, limit=limit)
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded",
            headers={"Retry-After": str(retry)},
        )


def rate_limit_ip(limit_name: str) -> Callable:
    """Per-IP limiter for public routes. `limit_name` is read from settings at call time."""
    async def dependency(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        ip = client_ip(request)
        _enforce(f"ip:{request.url.path}:{ip}", getattr(settings, limit_name),
                 scope="ip", route=request.url.path, who=ip)
    return dependency


def rate_limit_user(limit_name: str, tag: str) -> Callable:
    """Per-user limiter (keyed on JWT sub). Distinct `tag` -> independent bucket."""
    async def dependency(request: Request, user_id: uuid.UUID = Depends(get_current_user_id)) -> uuid.UUID:
        if settings.rate_limit_enabled:
            _enforce(f"user:{tag}:{user_id}", getattr(settings, limit_name),
                     scope="user", route=request.url.path, who=str(user_id))
        return user_id
    return dependency
