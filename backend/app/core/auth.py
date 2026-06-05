import time
import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientConnectionError, PyJWKClientError, get_unverified_header

from app.core.config import settings
from app.core.observability import log_event

# Supabase rotates its asymmetric signing keys; PyJWKClient caches the fetched
# JWKS and re-fetches on an unknown kid, so rotation needs no redeploy.
_jwk_client = PyJWKClient(settings.supabase_jwks_url, cache_keys=True)

_bearer = HTTPBearer(auto_error=False)

# kid -> monotonic() expiry. Only non-empty, confirmed-bad kids are stored.
# Never cache empty-string: absence of a kid field is not evidence the kid is invalid.
_negative_cache: dict[str, float] = {}


def _in_negative_cache(kid: str) -> bool:
    entry = _negative_cache.get(kid)
    if entry is None:
        return False
    if entry > time.monotonic():
        return True
    _negative_cache.pop(kid, None)   # lazy-evict expired entry
    return False


def _add_to_negative_cache(kid: str) -> None:
    if len(_negative_cache) >= settings.jwks_negative_cache_maxsize:
        _negative_cache.pop(next(iter(_negative_cache)), None)  # evict oldest
    _negative_cache[kid] = time.monotonic() + settings.jwks_negative_cache_ttl


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> uuid.UUID:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials

    # Extract kid from the unverified header — pure base64/JSON parse, no network.
    # DecodeError (malformed token) is a PyJWTError subclass; catch it early so the
    # negative-cache check and JWKS path are never reached for garbage input.
    try:
        kid = get_unverified_header(token).get("kid") or ""
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Short-circuit: kid already confirmed absent from JWKS — no upstream fetch needed.
    # Empty kid is never cached: absence of a kid field ≠ confirmed bad kid.
    if kid and _in_negative_cache(kid):
        log_event("auth.negative_cache.hit", kid=kid[:8])
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Generic 401 on every failure path — specific reason is an internal detail.
    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["ES256"],
            issuer=settings.supabase_issuer,
            audience=settings.supabase_jwt_audience,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
        return uuid.UUID(claims["sub"])
    except PyJWKClientConnectionError:
        # Network failure reaching Supabase JWKS endpoint — do NOT cache negatively;
        # the kid may be valid and the outage transient.
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except PyJWKClientError:
        # kid confirmed absent from JWKS after a forced refresh — safe to cache.
        if kid:
            _add_to_negative_cache(kid)
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
