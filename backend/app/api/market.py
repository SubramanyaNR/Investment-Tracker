from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.cache import market_cache
from app.core.ratelimit import rate_limit_ip
from app.integrations.coingecko import get_top_cryptos
from app.integrations.mfapi import get_latest_nav, search_schemes

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/crypto/top", dependencies=[Depends(rate_limit_ip("rl_market_default"))])
async def top_cryptos():
    try:
        return await get_top_cryptos()
    except Exception:
        raise HTTPException(status_code=502, detail="Upstream market data unavailable")


@router.get("/mutual-funds/search", dependencies=[Depends(rate_limit_ip("rl_market_search"))])
async def search_mutual_funds(q: str = Query(..., min_length=3)):
    try:
        return await search_schemes(q)
    except Exception:
        raise HTTPException(status_code=502, detail="Upstream market data unavailable")


@router.get("/mutual-funds/{scheme_code}/nav", dependencies=[Depends(rate_limit_ip("rl_market_default"))])
async def get_mf_nav(scheme_code: str):
    try:
        return await get_latest_nav(scheme_code)
    except Exception:
        raise HTTPException(status_code=502, detail="Upstream market data unavailable")


@router.get("/freshness")
async def market_freshness():
    """Return the last fetch timestamps (Unix epoch seconds) for crypto and MF price caches.

    Returns null for a category if no prices have been fetched yet this process lifetime.
    Frontend uses these to display "Prices updated X min ago" labels.
    """
    return {
        "crypto_updated_at": market_cache.latest_fetch("cg:"),
        "mf_updated_at": market_cache.latest_fetch("mf:nav:"),
    }
