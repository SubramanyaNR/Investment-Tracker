import httpx

from app.core.cache import market_cache
from app.core.config import settings


async def get_crypto_prices(ids: list[str], currency: str = "inr") -> dict:
    key = f"cg:prices:{currency}:{','.join(sorted(ids))}"

    async def _fetch() -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{settings.coingecko_base_url}/simple/price",
                params={"ids": ",".join(ids), "vs_currencies": currency},
            )
            response.raise_for_status()
            return response.json()

    return await market_cache.get_or_fetch(key, settings.cache_ttl_crypto, _fetch, fn="get_crypto_prices")


async def get_top_cryptos(currency: str = "inr", limit: int = 10) -> list[dict]:
    key = f"cg:top:{currency}:{limit}"

    async def _fetch() -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{settings.coingecko_base_url}/coins/markets",
                params={
                    "vs_currency": currency,
                    "order": "market_cap_desc",
                    "per_page": limit,
                    "page": 1,
                },
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "id": coin["id"],
                    "name": coin["name"],
                    "symbol": coin["symbol"].upper(),
                    "image": coin["image"],
                    "current_price": coin["current_price"],
                    "market_cap_rank": coin["market_cap_rank"],
                }
                for coin in data
            ]

    return await market_cache.get_or_fetch(key, settings.cache_ttl_crypto, _fetch, fn="get_top_cryptos")
