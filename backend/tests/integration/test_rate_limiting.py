"""Integration tests for A5 rate limiting through the real app.

Per-IP on public /market/* and per-user on authenticated routes both return 429 +
Retry-After once the (lowered) limit is exceeded.
"""
import uuid

import pytest

import app.api.market as market_mod
from app.core.cache import market_cache
from app.core.config import settings
from app.core.ratelimit import limiter

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_market_per_ip_429(anon_client, monkeypatch):
    async def _fake_top():
        return []

    monkeypatch.setattr(market_mod, "get_top_cryptos", _fake_top)  # no network
    monkeypatch.setattr(settings, "rl_market_default", 3)
    limiter.clear()
    market_cache.clear()

    codes = [(await anon_client.get("/market/crypto/top")).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3:] == [429, 429]

    resp = await anon_client.get("/market/crypto/top")
    assert resp.status_code == 429
    assert "retry-after" in {k.lower() for k in resp.headers}


async def test_authenticated_per_user_429(api, monkeypatch):
    monkeypatch.setattr(settings, "rl_user_general", 3)
    limiter.clear()
    user = uuid.uuid4()

    codes = [(await api.as_user(user).get("/dashboard")).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[-1] == 429
