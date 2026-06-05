"""Endpoint authorization matrix — every protected route rejects an unauthenticated
caller with 401; public routes do not. (SECURITY-AUDIT §4, enforcement half.)"""
import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_AID = uuid.uuid4()
_ASSET_BODY = {"name": "x", "asset_type": "CRYPTO", "category": "Crypto", "liquidity_tier": "liquid"}

# (method, path, json) — valid bodies so auth, not validation, is the failing gate.
PROTECTED = [
    ("GET", "/dashboard", None),
    ("GET", "/assets", None),
    ("GET", "/transactions", None),
    ("GET", "/valuations/latest", None),
    ("GET", "/snapshots", None),
    ("GET", "/insights/latest", None),
    ("POST", "/assets", _ASSET_BODY),
    ("POST", "/valuations/recalculate", None),
    ("POST", "/insights/refresh", None),
    ("DELETE", f"/assets/{_AID}", None),
    ("POST", f"/assets/{_AID}/sell-crypto", {"quantity": 1}),
    ("POST", f"/assets/{_AID}/redeem-mf", {"units": 1}),
    ("POST", f"/assets/{_AID}/top-up", {"amount": 1}),
    ("DELETE", "/account", None),
]


@pytest.mark.parametrize("method,path,body", PROTECTED)
async def test_protected_endpoint_requires_auth(anon_client, method, path, body):
    resp = await anon_client.request(method, path, json=body)
    assert resp.status_code == 401, f"{method} {path} -> {resp.status_code}"


async def test_health_is_public(anon_client):
    resp = await anon_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
