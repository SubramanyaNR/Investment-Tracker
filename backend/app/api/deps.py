import uuid

from fastapi import Depends

from app.core.auth import get_current_user_id
from app.db.session import AsyncSessionLocal


async def get_session(user_id: uuid.UUID = Depends(get_current_user_id)):
    """Request-scoped DB session bound to the caller's identity.

    Stashing user_id in session.info lets the after_begin RLS hook set the
    per-tenant GUC on every transaction this session opens.
    """
    session = AsyncSessionLocal()
    session.info["user_id"] = user_id
    try:
        yield session
    finally:
        await session.close()
