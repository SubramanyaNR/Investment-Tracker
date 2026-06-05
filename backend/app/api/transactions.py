import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from app.api.deps import get_session
from app.db.models import Transaction, Asset
from app.core.auth import get_current_user_id

router = APIRouter()


@router.get("/transactions")
async def list_transactions(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    total_result = await session.execute(
        select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)
    )
    total = total_result.scalar_one()

    result = await session.execute(
        select(Transaction, Asset)
        .join(Asset, Transaction.asset_id == Asset.id)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()
    return {
        "items": [
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
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
