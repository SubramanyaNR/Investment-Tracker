from fastapi import APIRouter, HTTPException, Query
from app.integrations.coingecko import get_top_cryptos
from app.integrations.mfapi import search_schemes

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/crypto/top")
async def top_cryptos():
    try:
        return await get_top_cryptos()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CoinGecko error: {str(e)}")


@router.get("/mutual-funds/search")
async def search_mutual_funds(q: str = Query(..., min_length=3)):
    try:
        return await search_schemes(q)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MFAPI error: {str(e)}")
