import uuid
import sqlalchemy as sa
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

USER_P = uuid.UUID("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa")

_TABLES = (
    "transactions", "valuation_history", "crypto_holdings", "fixed_income_holdings",
    "mutual_fund_holdings", "manual_holdings", "assets",
)

@pytest.fixture
async def seed_assets(api, admin_engine):
    # Wipe USER_P's data so tests don't accumulate across runs
    async with admin_engine.begin() as conn:
        for table in _TABLES:
            await conn.execute(sa.text(f"DELETE FROM {table} WHERE user_id = :uid"), {"uid": USER_P})

    assets = [
        {"name": "Asset A", "asset_type": "CRYPTO", "category": "crypto", "liquidity_tier": "LIQUID", "coingecko_id": "bitcoin", "symbol": "btc", "quantity": 1, "avg_buy_price": 50000},
        {"name": "Asset B", "asset_type": "MUTUAL_FUND", "category": "equity", "liquidity_tier": "LIQUID", "scheme_code": "123", "amount_invested": 1000, "nav_at_purchase": 10},
        {"name": "Asset C", "asset_type": "SAVINGS_ACC", "category": "savings", "liquidity_tier": "LIQUID", "principal": 5000, "annual_rate": 4, "start_date": "2024-01-01"},
    ]
    for a in assets:
        await api.as_user(USER_P).post("/assets", json=a)


async def test_assets_pagination_defaults(api, seed_assets):
    """AC1: response is paginated envelope with correct default fields."""
    resp = await api.as_user(USER_P).get("/assets")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] == 3
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert len(data["items"]) == 3


async def test_assets_pagination_limit(api, seed_assets):
    """AC2: limit param caps items returned; total still reflects full count."""
    resp = await api.as_user(USER_P).get("/assets?limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["limit"] == 2
    assert len(data["items"]) == 2


async def test_assets_pagination_offset(api, seed_assets):
    """AC2: offset skips rows; order is asset_type ASC, name ASC."""
    resp0 = await api.as_user(USER_P).get("/assets?limit=1&offset=0")
    resp1 = await api.as_user(USER_P).get("/assets?limit=1&offset=1")
    assert resp0.json()["items"][0]["name"] == "Asset A"
    assert resp1.json()["items"][0]["name"] == "Asset B"


async def test_assets_pagination_max_limit(api):
    """AC3: limit > 200 and limit=0 are rejected with 422."""
    assert (await api.as_user(USER_P).get("/assets?limit=201")).status_code == 422
    assert (await api.as_user(USER_P).get("/assets?limit=0")).status_code == 422


async def test_assets_pagination_offset_beyond_total(api, seed_assets):
    """offset beyond total returns empty items, not an error."""
    resp = await api.as_user(USER_P).get("/assets?offset=1000")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 3


async def test_assets_pagination_ordering(api, seed_assets):
    """Stable sort: asset_type ASC then name ASC across all 3 items."""
    resp = await api.as_user(USER_P).get("/assets")
    data = resp.json()
    names = [a["name"] for a in data["items"]]
    assert names == ["Asset A", "Asset B", "Asset C"]
