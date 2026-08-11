import uuid

from fastapi import Depends, Request

from app.core.auth import get_current_user_id
from app.db.session import AsyncSessionLocal


async def get_session(request: Request, user_id: uuid.UUID = Depends(get_current_user_id)):
    """Request-scoped DB session bound to the caller's identity.

    Stamps user_id on request.state so the access log can attribute the request.
    Every query still filters by user_id explicitly at the app layer (RLS was
    removed under architecture-002 Phase 2 — single-user model, no longer needed).
    """
    request.state.user_id = str(user_id)
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
