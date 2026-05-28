from fastapi import APIRouter, HTTPException
from app.integrations.coingecko import get_top_cryptos

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/crypto/top")
async def top_cryptos():
    try:
        return await get_top_cryptos()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CoinGecko error: {str(e)}")
