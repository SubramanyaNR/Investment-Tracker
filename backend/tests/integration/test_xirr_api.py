"""Integration tests for F5 — XIRR API.

Q1 — User with transactions → XIRR not null.
Q2 — User with no transactions → XIRR null, empty assets.
Q3 — User with only manual assets → XIRR null, manual_assets_excluded true.
Q4 — Mixed live + manual → XIRR excludes manual, flag set.
Q5 — Unauthenticated GET /xirr → 401.
Q6 — User journey: user loads XIRR data and sees it on the dashboard.
"""
import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
import sqlalchemy as sa

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

USER_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

_TRUNCATE = (
    "transactions", "valuation_history", "crypto_holdings", "fixed_income_holdings",
    "mutual_fund_holdings", "manual_holdings", "portfolio_snapshots", "ai_insights", "assets",
)


@pytest_asyncio.fixture(autouse=True)
async def clean_db(admin_engine):
    from app.core.ratelimit import limiter
    limiter._hits.clear()
    async with admin_engine.begin() as conn:
        await conn.execute(sa.text(f"TRUNCATE {', '.join(_TRUNCATE)} CASCADE"))
    yield


async def _seed_crypto_asset(conn, user_id: uuid.UUID, invested: float, current: float) -> uuid.UUID:
    """Insert asset + crypto_holding + transaction + valuation_history."""
    aid = uuid.uuid4()
    cg_id = f"bitcoin-{aid.hex[:6]}"
    start = date.today() - timedelta(days=365)
    today = date.today()
    await conn.execute(
        sa.text("INSERT INTO assets (id,user_id,name,asset_type,category,liquidity_tier) "
                "VALUES (:id,:uid,'Bitcoin','CRYPTO','crypto','liquid')"),
        {"id": str(aid), "uid": str(user_id)},
    )
    await conn.execute(
        sa.text("INSERT INTO crypto_holdings (asset_id,user_id,coingecko_id,symbol,quantity,avg_buy_price) "
                "VALUES (:id,:uid,:cg,'BTC',0.01,:price)"),
        {"id": str(aid), "uid": str(user_id), "cg": cg_id, "price": invested / 0.01},
    )
    await conn.execute(
        sa.text("INSERT INTO transactions (id,user_id,asset_id,transaction_type,transaction_date,amount,units,price_per_unit) "
                "VALUES (gen_random_uuid(),:uid,:aid,'BUY',:dt,:amt,0.01,:price)"),
        {"uid": str(user_id), "aid": str(aid), "dt": start,
         "amt": invested, "price": invested / 0.01},
    )
    await conn.execute(
        sa.text("INSERT INTO valuation_history (id,user_id,asset_id,valuation_date,invested_amount,current_value,pnl,source) "
                "VALUES (gen_random_uuid(),:uid,:aid,:today,:inv,:cur,:pnl,'test')"),
        {"uid": str(user_id), "aid": str(aid), "today": today,
         "inv": invested, "cur": current, "pnl": current - invested},
    )
    return aid


async def _seed_manual_asset(conn, user_id: uuid.UUID, cost: float, value: float) -> uuid.UUID:
    aid = uuid.uuid4()
    today = date.today()
    await conn.execute(
        sa.text("INSERT INTO assets (id,user_id,name,asset_type,category,liquidity_tier) "
                "VALUES (:id,:uid,'Real Estate','MANUAL','equity','liquid')"),
        {"id": str(aid), "uid": str(user_id)},
    )
    await conn.execute(
        sa.text("INSERT INTO manual_holdings (asset_id,user_id,cost_basis,current_value) "
                "VALUES (:id,:uid,:cost,:val)"),
        {"id": str(aid), "uid": str(user_id), "cost": cost, "val": value},
    )
    await conn.execute(
        sa.text("INSERT INTO valuation_history (id,user_id,asset_id,valuation_date,invested_amount,current_value,pnl,source) "
                "VALUES (gen_random_uuid(),:uid,:aid,:today,:inv,:cur,:pnl,'manual')"),
        {"uid": str(user_id), "aid": str(aid), "today": today,
         "inv": cost, "cur": value, "pnl": value - cost},
    )
    return aid


async def test_xirr_with_transactions(api, admin_engine):
    """Q1 — User with crypto asset + transaction → portfolio XIRR is not null."""
    async with admin_engine.begin() as conn:
        await _seed_crypto_asset(conn, USER_A, invested=50_000, current=65_000)

    resp = await api.as_user(USER_A).get("/xirr")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["portfolio_xirr"] is not None
    assert data["portfolio_xirr"] > 0
    assert data["portfolio_start_date"] is not None
    assert len(data["assets"]) == 1
    assert data["assets"][0]["xirr"] is not None
    assert data["assets"][0]["total_invested"] == 50_000.0
    assert data["assets"][0]["current_value"] == 65_000.0


async def test_xirr_no_transactions(api, admin_engine):
    """Q2 — User with no assets → null XIRR, empty assets list."""
    resp = await api.as_user(USER_A).get("/xirr")
    assert resp.status_code == 200
    data = resp.json()
    assert data["portfolio_xirr"] is None
    assert data["portfolio_start_date"] is None
    assert data["assets"] == []
    assert data["manual_assets_excluded"] is False


async def test_xirr_only_manual_assets(api, admin_engine):
    """Q3 — Only manual assets → null XIRR, manual_assets_excluded true."""
    async with admin_engine.begin() as conn:
        await _seed_manual_asset(conn, USER_A, cost=500_000, value=650_000)

    resp = await api.as_user(USER_A).get("/xirr")
    assert resp.status_code == 200
    data = resp.json()
    assert data["portfolio_xirr"] is None
    assert data["manual_assets_excluded"] is True
    assert data["assets"] == []


async def test_xirr_excludes_manual_from_mixed_portfolio(api, admin_engine):
    """Q4 — Live + manual assets → XIRR from live only, manual_assets_excluded true."""
    async with admin_engine.begin() as conn:
        await _seed_crypto_asset(conn, USER_A, invested=50_000, current=65_000)
        await _seed_manual_asset(conn, USER_A, cost=500_000, value=650_000)

    resp = await api.as_user(USER_A).get("/xirr")
    assert resp.status_code == 200
    data = resp.json()
    assert data["portfolio_xirr"] is not None    # computed from live asset only
    assert data["manual_assets_excluded"] is True
    assert len(data["assets"]) == 1              # only the CRYPTO asset
    assert data["assets"][0]["asset_type"] == "CRYPTO"


async def test_xirr_unauthenticated(anon_client):
    """Q5 — Anonymous GET /xirr → 401."""
    resp = await anon_client.get("/xirr")
    assert resp.status_code == 401


async def test_xirr_cross_user_isolation(api, admin_engine):
    """Q5b — User B cannot see User A's XIRR data."""
    async with admin_engine.begin() as conn:
        await _seed_crypto_asset(conn, USER_A, invested=50_000, current=65_000)

    resp_b = await api.as_user(USER_B).get("/xirr")
    assert resp_b.status_code == 200
    data = resp_b.json()
    assert data["portfolio_xirr"] is None    # B has no assets
    assert data["assets"] == []


async def test_xirr_user_journey_response_shape(api, admin_engine):
    """J1 — Verify response has all fields the frontend needs to render the KPI card."""
    async with admin_engine.begin() as conn:
        await _seed_crypto_asset(conn, USER_A, invested=50_000, current=65_000)

    resp = await api.as_user(USER_A).get("/xirr")
    assert resp.status_code == 200
    data = resp.json()

    # All fields the frontend KPI card and holdings row depend on
    assert "portfolio_xirr" in data
    assert "portfolio_start_date" in data
    assert "manual_assets_excluded" in data
    assert "assets" in data

    asset = data["assets"][0]
    assert "asset_id" in asset
    assert "asset_name" in asset
    assert "asset_type" in asset
    assert "xirr" in asset
    assert "start_date" in asset
    assert "total_invested" in asset
    assert "current_value" in asset
