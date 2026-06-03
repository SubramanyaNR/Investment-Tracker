import uuid
from fastapi import APIRouter, Depends
from app.db.session import AsyncSessionLocal
from app.services.portfolio import get_dashboard
from app.core.auth import get_current_user_id

router = APIRouter()


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/dashboard")
async def dashboard(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await get_dashboard(session, user_id)
