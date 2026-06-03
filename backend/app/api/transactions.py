import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Transaction, Asset
from app.core.auth import get_current_user_id

router = APIRouter()


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/transactions")
async def list_transactions(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    result = await session.execute(
        select(Transaction, Asset)
        .join(Asset, Transaction.asset_id == Asset.id)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
    )
    rows = result.all()
    return [
        {
            "id": str(t.id),
            "asset_id": str(t.asset_id),
            "asset_name": a.name,
            "asset_type": a.asset_type,
            "transaction_type": t.transaction_type,
            "transaction_date": str(t.transaction_date),
            "amount": float(t.amount),
            "units": float(t.units) if t.units is not None else None,
            "price_per_unit": float(t.price_per_unit) if t.price_per_unit is not None else None,
        }
        for t, a in rows
    ]
