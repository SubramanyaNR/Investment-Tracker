import httpx

from app.core.cache import market_cache
from app.core.config import settings


async def get_latest_nav(scheme_code: str) -> dict:
    key = f"mf:nav:{scheme_code}"

    async def _fetch() -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{settings.mfapi_base_url}/{scheme_code}")
            response.raise_for_status()
            data = response.json()
            latest = data["data"][0]
            return {
                "scheme_code": scheme_code,
                "nav": float(latest["nav"]),
                "date": latest["date"],
            }

    return await market_cache.get_or_fetch(key, settings.cache_ttl_nav, _fetch, fn="get_latest_nav")


async def search_schemes(query: str) -> list[dict]:
    key = f"mf:search:{query.strip().lower()}"

    async def _fetch() -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{settings.mfapi_base_url}/search",
                params={"q": query},
            )
            response.raise_for_status()
            results = response.json()
            return [
                {"scheme_code": str(s["schemeCode"]), "name": s["schemeName"]}
                for s in results[:20]
            ]

    return await market_cache.get_or_fetch(key, settings.cache_ttl_search, _fetch, fn="search_schemes")
