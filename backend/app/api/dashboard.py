import uuid
from fastapi import APIRouter, Depends
from app.api.deps import get_session
from app.services.portfolio import get_dashboard
from app.core.auth import get_current_user_id

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await get_dashboard(session, user_id)
