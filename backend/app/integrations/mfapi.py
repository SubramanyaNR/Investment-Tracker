import httpx
from app.core.config import settings


async def get_latest_nav(scheme_code: str) -> dict:
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
