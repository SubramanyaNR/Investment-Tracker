"""Integration tests for F9/F10 — Performance API.

Q1 — Monthly: assets with data → top/bottom 3 returned correctly.
Q2 — Monthly: no data this month → has_data false, empty lists.
Q3 — Daily: today + yesterday rows → correct ranking.
Q4 — Daily: no yesterday rows → has_data false, empty lists.
Q5 — FI/MANUAL assets excluded from results.
Q6 — Unauthenticated → 401.
Q7 — Cross-user isolation.
J1 — User journey: response shape has all fields frontend needs.
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


async def _seed_valuation(
    conn, user_id, asset_id, val_date: date,
    invested: float, current: float,
    price_per_unit: float | None = None,
):
    await conn.execute(
        sa.text(
            "INSERT INTO valuation_history "
            "(id,user_id,asset_id,valuation_date,invested_amount,current_value,pnl,price_per_unit,source) "
            "VALUES (gen_random_uuid(),:uid,:aid,:dt,:inv,:cur,:pnl,:ppu,'test')"
        ),
        {"uid": str(user_id), "aid": str(asset_id), "dt": val_date,
         "inv": invested, "cur": current, "pnl": current - invested,
         "ppu": price_per_unit},
    )


async def _seed_asset(conn, user_id, name: str, asset_type: str = "CRYPTO") -> uuid.UUID:
    aid = uuid.uuid4()
    await conn.execute(
        sa.text(
            "INSERT INTO assets (id,user_id,name,asset_type,category,liquidity_tier) "
            "VALUES (:id,:uid,:name,:atype,'crypto','liquid')"
        ),
        {"id": str(aid), "uid": str(user_id), "name": name, "atype": asset_type},
    )
    return aid


async def test_monthly_performance_with_data(api, admin_engine):
    """Q1 — Assets with start + end valuations this month → ranked result."""
    today = date.today()
    month_start = today.replace(day=1)
    if month_start == today:
        pytest.skip("Skipping: test requires at least 2 different days in the month")

    async with admin_engine.begin() as conn:
        btc = await _seed_asset(conn, USER_A, "Bitcoin")
        eth = await _seed_asset(conn, USER_A, "Ethereum")

        # BTC up 10% this month (price: 100 → 110)
        await _seed_valuation(conn, USER_A, btc, month_start, 50_000, 50_000, price_per_unit=100.0)
        await _seed_valuation(conn, USER_A, btc, today,       50_000, 55_000, price_per_unit=110.0)
        # ETH down 5% this month (price: 200 → 190)
        await _seed_valuation(conn, USER_A, eth, month_start, 20_000, 20_000, price_per_unit=200.0)
        await _seed_valuation(conn, USER_A, eth, today,       20_000, 19_000, price_per_unit=190.0)

    resp = await api.as_user(USER_A).get("/performance/monthly")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_data"] is True
    assert data["period"] == "monthly"
    assert len(data["top"]) >= 1
    assert len(data["bottom"]) >= 1
    assert data["top"][0]["asset_name"] == "Bitcoin"
    assert data["top"][0]["pct_change"] == 10.0
    assert data["bottom"][0]["asset_name"] == "Ethereum"
    assert data["bottom"][0]["pct_change"] == -5.0


async def test_monthly_performance_no_data(api):
    """Q2 — No valuation rows → has_data false."""
    resp = await api.as_user(USER_A).get("/performance/monthly")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_data"] is False
    assert data["top"] == []
    assert data["bottom"] == []


async def test_daily_performance_with_data(api, admin_engine):
    """Q3 — Today + yesterday rows → correct daily ranking."""
    today     = date.today()
    yesterday = today - timedelta(days=1)

    async with admin_engine.begin() as conn:
        btc = await _seed_asset(conn, USER_A, "Bitcoin")
        ppf = await _seed_asset(conn, USER_A, "PPFAS MF", "MUTUAL_FUND")

        # BTC up 6% today (price: 100 → 106)
        await _seed_valuation(conn, USER_A, btc, yesterday, 50_000, 50_000, price_per_unit=100.0)
        await _seed_valuation(conn, USER_A, btc, today,     50_000, 53_000, price_per_unit=106.0)
        # MF up 0.5% today (NAV: 100 → 100.5)
        await _seed_valuation(conn, USER_A, ppf, yesterday, 10_000, 10_000, price_per_unit=100.0)
        await _seed_valuation(conn, USER_A, ppf, today,     10_000, 10_050, price_per_unit=100.5)

    resp = await api.as_user(USER_A).get("/performance/daily")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_data"] is True
    assert data["period"] == "daily"
    assert data["top"][0]["asset_name"] == "Bitcoin"
    assert data["top"][0]["pct_change"] == 6.0


async def test_daily_performance_no_yesterday(api, admin_engine):
    """Q4 — Only today's rows → has_data false (no yesterday to compare)."""
    today = date.today()
    async with admin_engine.begin() as conn:
        btc = await _seed_asset(conn, USER_A, "Bitcoin")
        await _seed_valuation(conn, USER_A, btc, today, 50_000, 53_000, price_per_unit=106.0)

    resp = await api.as_user(USER_A).get("/performance/daily")
    assert resp.status_code == 200
    assert resp.json()["has_data"] is False


async def test_fi_and_manual_assets_excluded(api, admin_engine):
    """Q5 — FI and MANUAL assets do not appear in performance results."""
    today = date.today()
    month_start = today.replace(day=1)
    if month_start == today:
        pytest.skip("Skipping: test requires at least 2 different days in the month")

    async with admin_engine.begin() as conn:
        fd = await _seed_asset(conn, USER_A, "SBI FD", "FD")
        manual = await _seed_asset(conn, USER_A, "Real Estate", "MANUAL")

        await _seed_valuation(conn, USER_A, fd, month_start, 100_000, 100_000)
        await _seed_valuation(conn, USER_A, fd, today,       100_000, 101_000)
        await _seed_valuation(conn, USER_A, manual, month_start, 500_000, 500_000)
        await _seed_valuation(conn, USER_A, manual, today,       500_000, 520_000)

    resp = await api.as_user(USER_A).get("/performance/monthly")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_data"] is False   # no CRYPTO/MF assets
    all_names = [e["asset_name"] for e in data["top"] + data["bottom"]]
    assert "SBI FD" not in all_names
    assert "Real Estate" not in all_names


async def test_performance_unauthenticated(anon_client):
    """Q6 — Anonymous access → 401."""
    r1 = await anon_client.get("/performance/monthly")
    r2 = await anon_client.get("/performance/daily")
    assert r1.status_code == 401
    assert r2.status_code == 401


async def test_performance_cross_user_isolation(api, admin_engine):
    """Q7 — User B sees empty results when only User A has assets."""
    today = date.today()
    month_start = today.replace(day=1)
    if month_start == today:
        pytest.skip("Skipping: test requires at least 2 different days in the month")

    async with admin_engine.begin() as conn:
        btc = await _seed_asset(conn, USER_A, "Bitcoin")
        await _seed_valuation(conn, USER_A, btc, month_start, 50_000, 50_000, price_per_unit=100.0)
        await _seed_valuation(conn, USER_A, btc, today,       50_000, 55_000, price_per_unit=110.0)

    resp = await api.as_user(USER_B).get("/performance/monthly")
    assert resp.status_code == 200
    assert resp.json()["has_data"] is False


async def test_monthly_response_shape(api, admin_engine):
    """J1 — Response shape has all fields frontend needs."""
    today = date.today()
    month_start = today.replace(day=1)
    if month_start == today:
        pytest.skip("Skipping: test requires at least 2 different days in the month")

    async with admin_engine.begin() as conn:
        btc = await _seed_asset(conn, USER_A, "Bitcoin")
        await _seed_valuation(conn, USER_A, btc, month_start, 50_000, 50_000, price_per_unit=100.0)
        await _seed_valuation(conn, USER_A, btc, today,       50_000, 55_000, price_per_unit=110.0)

    resp = await api.as_user(USER_A).get("/performance/monthly")
    assert resp.status_code == 200
    data = resp.json()

    assert "top" in data
    assert "bottom" in data
    assert "has_data" in data
    assert "period" in data
    assert "period_label" in data

    if data["top"]:
        entry = data["top"][0]
        for field in ("asset_id", "asset_name", "asset_type", "pct_change", "start_value", "end_value"):
            assert field in entry


async def test_daily_capital_addition_uses_price_per_unit(api, admin_engine):
    """R1 — Capital added between yesterday and today must not inflate pct_change.

    Scenario: user doubled their BTC position overnight (invested jumps from
    50k to 100k). BTC price only moved +5%. Without price_per_unit the ratio
    of current_values would show ~110% (capital + price), not the real 5%.
    """
    today     = date.today()
    yesterday = today - timedelta(days=1)

    async with admin_engine.begin() as conn:
        btc = await _seed_asset(conn, USER_A, "Bitcoin")

        # Yesterday: 1 BTC @ price 50_000
        await _seed_valuation(
            conn, USER_A, btc, yesterday,
            invested=50_000, current=50_000, price_per_unit=50_000.0,
        )
        # Today: 2 BTC @ price 52_500 (price up 5%; user also doubled position)
        await _seed_valuation(
            conn, USER_A, btc, today,
            invested=100_000, current=105_000, price_per_unit=52_500.0,
        )

    resp = await api.as_user(USER_A).get("/performance/daily")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_data"] is True
    top_entry = data["top"][0]
    assert top_entry["asset_name"] == "Bitcoin"
    # Must reflect the 5% price move, NOT the ~110% holding-value change
    assert abs(top_entry["pct_change"] - 5.0) < 0.01


async def test_monthly_capital_addition_uses_price_per_unit(api, admin_engine):
    """R2 — Capital added mid-month must not inflate monthly pct_change."""
    today      = date.today()
    month_start = today.replace(day=1)
    if month_start == today:
        pytest.skip("Skipping: test requires at least 2 different days in the month")

    async with admin_engine.begin() as conn:
        btc = await _seed_asset(conn, USER_A, "Bitcoin")

        # Month start: 1 BTC @ price 40_000
        await _seed_valuation(
            conn, USER_A, btc, month_start,
            invested=40_000, current=40_000, price_per_unit=40_000.0,
        )
        # Today: 2 BTC @ price 42_000 (price up 5%; user also doubled position)
        await _seed_valuation(
            conn, USER_A, btc, today,
            invested=80_000, current=84_000, price_per_unit=42_000.0,
        )

    resp = await api.as_user(USER_A).get("/performance/monthly")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_data"] is True
    top_entry = data["top"][0]
    # Must reflect the 5% price move, NOT the ~110% holding-value change
    assert abs(top_entry["pct_change"] - 5.0) < 0.01


async def test_daily_fallback_to_current_value_when_no_price_per_unit(api, admin_engine):
    """R3 — Pre-migration rows (price_per_unit NULL) fall back to current_value comparison."""
    today     = date.today()
    yesterday = today - timedelta(days=1)

    async with admin_engine.begin() as conn:
        btc = await _seed_asset(conn, USER_A, "Bitcoin")

        # Both rows without price_per_unit (simulates pre-migration data)
        await _seed_valuation(conn, USER_A, btc, yesterday, 50_000, 50_000, price_per_unit=None)
        await _seed_valuation(conn, USER_A, btc, today,     50_000, 53_000, price_per_unit=None)

    resp = await api.as_user(USER_A).get("/performance/daily")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_data"] is True
    # Falls back to current_value: (53000 - 50000) / 50000 * 100 = 6.0%
    assert abs(data["top"][0]["pct_change"] - 6.0) < 0.01
