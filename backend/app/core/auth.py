import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import settings

# Supabase rotates its asymmetric signing keys; PyJWKClient caches the fetched
# JWKS and re-fetches on an unknown kid, so rotation needs no redeploy.
_jwk_client = PyJWKClient(settings.supabase_jwks_url, cache_keys=True)

_bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> uuid.UUID:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = credentials.credentials
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
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

    sub = claims.get("sub")
    try:
        return uuid.UUID(sub)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid subject claim") from exc
