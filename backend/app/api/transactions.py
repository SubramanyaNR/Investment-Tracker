import uuid
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from app.api.deps import get_session
from app.db.models import Transaction, Asset
from app.core.auth import get_current_user_id

router = APIRouter()


@router.get("/transactions")
async def list_transactions(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must not be after to_date")

    # Base filter: ownership
    filters = [Transaction.user_id == user_id]
    if from_date:
        filters.append(Transaction.transaction_date >= from_date)
    if to_date:
        filters.append(Transaction.transaction_date <= to_date)

    total_result = await session.execute(
        select(func.count()).select_from(Transaction).where(*filters)
    )
    total = total_result.scalar_one()

    result = await session.execute(
        select(Transaction, Asset)
        .join(Asset, Transaction.asset_id == Asset.id)
        .where(*filters)
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
