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
