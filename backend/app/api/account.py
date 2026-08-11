import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import delete
from app.api.deps import get_session
from app.db.models import Asset, PortfolioSnapshot, AIInsight
from app.core.auth import get_current_user_id

router = APIRouter()


@router.delete("/account")
async def delete_account(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Purge all of the caller's data. Deleting assets cascades to transactions,
    valuations and holdings; snapshots and insights aren't asset-linked so are
    removed explicitly. Does not delete the user's login/admin account row."""
    await session.execute(delete(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user_id))
    await session.execute(delete(AIInsight).where(AIInsight.user_id == user_id))
    await session.execute(delete(Asset).where(Asset.user_id == user_id))
    await session.commit()
    return {"deleted": True}
