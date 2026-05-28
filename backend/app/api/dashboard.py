from fastapi import APIRouter, Depends
from app.db.session import AsyncSessionLocal
from app.services.portfolio import get_dashboard

router = APIRouter()


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/dashboard")
async def dashboard(session=Depends(get_session)):
    return await get_dashboard(session)
