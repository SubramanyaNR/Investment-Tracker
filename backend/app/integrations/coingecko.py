import httpx
from app.core.config import settings


async def get_crypto_prices(ids: list[str], currency: str = "inr") -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.coingecko_base_url}/simple/price",
            params={"ids": ",".join(ids), "vs_currencies": currency},
        )
        response.raise_for_status()
        return response.json()


async def get_top_cryptos(currency: str = "inr", limit: int = 10) -> list[dict]:
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
