import csv
import io
import uuid
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, and_, func
from app.api.deps import get_session
from app.db.models import Asset, Transaction, ValuationHistory, CryptoHolding, MutualFundHolding
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/export", tags=["export"])

IST = ZoneInfo("Asia/Kolkata")

def sanitize_csv_value(val):
    if val is None:
        return ""
    if isinstance(val, (int, float, Decimal)):
        return str(val)
    str_val = str(val)
    if str_val.startswith(('=', '+', '-', '@')):
        return "'" + str_val
    return str_val

@router.get("/holdings")
async def export_holdings(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    # Latest valuation per asset only
    subq = (
        select(
            ValuationHistory.asset_id,
            func.max(ValuationHistory.valuation_date).label("latest_date"),
        )
        .where(ValuationHistory.user_id == user_id)
        .group_by(ValuationHistory.asset_id)
        .subquery()
    )
    
    # Join with Asset to get names and types
    stmt = (
        select(Asset, ValuationHistory)
        .where(Asset.user_id == user_id)
        .join(
            ValuationHistory,
            and_(
                ValuationHistory.asset_id == Asset.id,
                ValuationHistory.user_id == user_id
            )
        )
        .join(
            subq,
            and_(
                ValuationHistory.asset_id == subq.c.asset_id,
                ValuationHistory.valuation_date == subq.c.latest_date,
            ),
        )
        .order_by(Asset.asset_type, Asset.name)
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    asset_ids = [r[0].id for r in rows]
    
    # Fetch units/quantity where applicable
    crypto_res = await session.execute(select(CryptoHolding).where(CryptoHolding.asset_id.in_(asset_ids)))
    crypto_map = {h.asset_id: h.quantity for h in crypto_res.scalars().all()}
    
    mf_res = await session.execute(select(MutualFundHolding).where(MutualFundHolding.asset_id.in_(asset_ids)))
    mf_map = {h.asset_id: h.units for h in mf_res.scalars().all()}
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers - human readable as requested by Investor Advisor
    writer.writerow([
        "Asset Name", "Asset Type", "Category", "Currency", 
        "Invested Amount", "Current Value", "P&L", 
        "Units/Quantity", "Price per Unit"
    ])
    
    for asset, val in rows:
        units = ""
        if asset.id in crypto_map:
            units = crypto_map[asset.id]
        elif asset.id in mf_map:
            units = mf_map[asset.id]
            
        writer.writerow([
            sanitize_csv_value(asset.name),
            asset.asset_type,
            asset.category,
            "INR",
            val.invested_amount,
            val.current_value,
            val.pnl,
            units,
            val.price_per_unit if val.price_per_unit is not None else ""
        ])
    
    now_ist = datetime.now(IST).strftime("%Y%m%d_%H%M")
    filename = f"wealthsignal_holdings_{now_ist}.csv"
    
    csv_content = output.getvalue()
    output.close()
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store"
        }
    )

@router.get("/transactions")
async def export_transactions(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    stmt = (
        select(Transaction, Asset)
        .join(Asset, Transaction.asset_id == Asset.id)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Date", "Asset Name", "Asset Type", "Transaction Type", 
        "Amount (INR)", "Units", "Price per Unit"
    ])
    
    for tx, asset in rows:
        writer.writerow([
            tx.transaction_date.isoformat(),
            sanitize_csv_value(asset.name),
            asset.asset_type,
            tx.transaction_type,
            tx.amount,
            tx.units if tx.units is not None else "",
            tx.price_per_unit if tx.price_per_unit is not None else ""
        ])
        
    now_ist = datetime.now(IST).strftime("%Y%m%d_%H%M")
    filename = f"wealthsignal_transactions_{now_ist}.csv"
    
    csv_content = output.getvalue()
    output.close()
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store"
        }
    )
