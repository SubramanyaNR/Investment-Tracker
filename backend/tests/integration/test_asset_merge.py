"""Integration tests for atomic asset merge — A10b.

Unique constraints uq_crypto_holdings_user_coingecko and uq_mf_holdings_user_scheme
prevent silent duplicate holdings. Application code handles IntegrityError on the
concurrent-first-insert race by rolling back and merging into the committed holding.

T-CONSTRAINT-1: DB rejects duplicate crypto holding (same user + coingecko_id)
T-CONSTRAINT-2: DB rejects duplicate MF holding (same user + scheme_code)
T-MERGE-CRYPTO:  Sequential POST /assets for same coin merges into one holding
T-MERGE-MF:      Sequential POST /assets for same scheme merges into one holding
T-CONCURRENT-CRYPTO: Concurrent POSTs same coin both return 200, one holding remains
T-CONCURRENT-MF:     Concurrent POSTs same scheme both return 200, one holding remains
"""
import asyncio
import uuid

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# Distinct user — no collision with USER_A/B (tenant isolation) or USER_C (snapshot tests).
USER_D = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")

_CRYPTO_PAYLOAD = {
    "name": "Test Coin D",
    "asset_type": "CRYPTO",
    "category": "Crypto",
    "liquidity_tier": "liquid",
    "coingecko_id": "test-coin-d-a10b",
    "symbol": "TCD",
    "quantity": "5",
    "avg_buy_price": "100",
}

_MF_PAYLOAD = {
    "name": "Test Fund D",
    "asset_type": "MUTUAL_FUND",
    "category": "Equity",
    "liquidity_tier": "medium",
    "scheme_code": "TEST-A10B-001",
    "amount_invested": "5000",
    "nav_at_purchase": "100",
}


@pytest_asyncio.fixture
async def merge_seed(admin_engine):
    """Clean state for USER_D before each test; teardown removes all USER_D rows."""
    async with admin_engine.begin() as conn:
        await conn.execute(
            sa.text("DELETE FROM portfolio_snapshots WHERE user_id = :uid"),
            {"uid": str(USER_D)},
        )
        await conn.execute(
            sa.text("DELETE FROM assets WHERE user_id = :uid"),
            {"uid": str(USER_D)},
        )
    yield {"user": USER_D}
    async with admin_engine.begin() as conn:
        await conn.execute(
            sa.text("DELETE FROM portfolio_snapshots WHERE user_id = :uid"),
            {"uid": str(USER_D)},
        )
        await conn.execute(
            sa.text("DELETE FROM assets WHERE user_id = :uid"),
            {"uid": str(USER_D)},
        )


async def _count(conn, table: str, user_id: uuid.UUID) -> int:
    row = await conn.execute(
        sa.text(f"SELECT COUNT(*) FROM {table} WHERE user_id = :uid"),
        {"uid": str(user_id)},
    )
    return row.scalar()


async def _scalar(conn, sql: str, params: dict):
    row = await conn.execute(sa.text(sql), params)
    return row.scalar()


# ── Constraint tests (raw SQL via admin engine) ──────────────────────────────

async def test_unique_constraint_prevents_duplicate_crypto(admin_engine, merge_seed):
    """T-CONSTRAINT-1: second INSERT with same (user_id, coingecko_id) raises IntegrityError."""
    user = merge_seed["user"]
    aid1, aid2 = uuid.uuid4(), uuid.uuid4()

    async with admin_engine.begin() as conn:
        for aid in [aid1, aid2]:
            await conn.execute(
                sa.text(
                    "INSERT INTO assets (id,user_id,name,asset_type,category,liquidity_tier) "
                    "VALUES (:id,:uid,'t','CRYPTO','Crypto','liquid')"
                ),
                {"id": str(aid), "uid": str(user)},
            )
        await conn.execute(
            sa.text(
                "INSERT INTO crypto_holdings (asset_id,user_id,coingecko_id,symbol,quantity,avg_buy_price) "
                "VALUES (:aid,:uid,'dup-coin','DC',1,100)"
            ),
            {"aid": str(aid1), "uid": str(user)},
        )

    with pytest.raises(IntegrityError):
        async with admin_engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO crypto_holdings (asset_id,user_id,coingecko_id,symbol,quantity,avg_buy_price) "
                    "VALUES (:aid,:uid,'dup-coin','DC',2,200)"
                ),
                {"aid": str(aid2), "uid": str(user)},
            )


async def test_unique_constraint_prevents_duplicate_mf(admin_engine, merge_seed):
    """T-CONSTRAINT-2: second INSERT with same (user_id, scheme_code) raises IntegrityError."""
    user = merge_seed["user"]
    aid1, aid2 = uuid.uuid4(), uuid.uuid4()

    async with admin_engine.begin() as conn:
        for aid in [aid1, aid2]:
            await conn.execute(
                sa.text(
                    "INSERT INTO assets (id,user_id,name,asset_type,category,liquidity_tier) "
                    "VALUES (:id,:uid,'t','MUTUAL_FUND','Equity','medium')"
                ),
                {"id": str(aid), "uid": str(user)},
            )
        await conn.execute(
            sa.text(
                "INSERT INTO mutual_fund_holdings (asset_id,user_id,scheme_code,units,nav_at_purchase) "
                "VALUES (:aid,:uid,'DUP-SCHEME',50,100)"
            ),
            {"aid": str(aid1), "uid": str(user)},
        )

    with pytest.raises(IntegrityError):
        async with admin_engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO mutual_fund_holdings (asset_id,user_id,scheme_code,units,nav_at_purchase) "
                    "VALUES (:aid,:uid,'DUP-SCHEME',30,120)"
                ),
                {"aid": str(aid2), "uid": str(user)},
            )


# ── Application-level merge tests (via API) ──────────────────────────────────

async def test_sequential_crypto_add_merges(api, merge_seed, admin_engine):
    """T-MERGE-CRYPTO: two sequential POSTs for same coin produce one holding with summed quantity."""
    user = merge_seed["user"]
    client = api.as_user(user)

    r1 = await client.post("/assets", json=_CRYPTO_PAYLOAD)
    assert r1.status_code == 200, r1.text

    r2 = await client.post("/assets", json=_CRYPTO_PAYLOAD)
    assert r2.status_code == 200, r2.text

    async with admin_engine.connect() as conn:
        asset_count = await _count(conn, "assets", user)
        holding_count = await _count(conn, "crypto_holdings", user)
        quantity = await _scalar(
            conn,
            "SELECT quantity FROM crypto_holdings WHERE user_id = :uid",
            {"uid": str(user)},
        )

    assert asset_count == 1, f"expected 1 asset row, found {asset_count}"
    assert holding_count == 1, f"expected 1 holding row, found {holding_count}"
    assert float(quantity) == 10.0, f"expected qty=10 (5+5), found {quantity}"


async def test_sequential_mf_add_merges(api, merge_seed, admin_engine):
    """T-MERGE-MF: two sequential POSTs for same scheme produce one holding with summed units."""
    user = merge_seed["user"]
    client = api.as_user(user)

    r1 = await client.post("/assets", json=_MF_PAYLOAD)
    assert r1.status_code == 200, r1.text

    r2 = await client.post("/assets", json=_MF_PAYLOAD)
    assert r2.status_code == 200, r2.text

    async with admin_engine.connect() as conn:
        asset_count = await _count(conn, "assets", user)
        holding_count = await _count(conn, "mutual_fund_holdings", user)
        units = await _scalar(
            conn,
            "SELECT units FROM mutual_fund_holdings WHERE user_id = :uid",
            {"uid": str(user)},
        )

    assert asset_count == 1, f"expected 1 asset row, found {asset_count}"
    assert holding_count == 1, f"expected 1 holding row, found {holding_count}"
    # 5000/100 = 50 units × 2 = 100
    assert float(units) == 100.0, f"expected units=100 (50+50), found {units}"


async def test_concurrent_crypto_add_both_succeed(api, merge_seed, admin_engine):
    """T-CONCURRENT-CRYPTO: concurrent POSTs for same coin both return 200; one holding remains."""
    user = merge_seed["user"]
    client = api.as_user(user)

    r1, r2 = await asyncio.gather(
        client.post("/assets", json=_CRYPTO_PAYLOAD),
        client.post("/assets", json=_CRYPTO_PAYLOAD),
    )

    assert r1.status_code == 200, f"r1 failed: {r1.text}"
    assert r2.status_code == 200, f"r2 failed: {r2.text}"

    async with admin_engine.connect() as conn:
        asset_count = await _count(conn, "assets", user)
        holding_count = await _count(conn, "crypto_holdings", user)

    assert asset_count == 1, f"expected 1 asset row, found {asset_count}"
    assert holding_count == 1, f"expected 1 crypto holding, found {holding_count}"


async def test_concurrent_mf_add_both_succeed(api, merge_seed, admin_engine):
    """T-CONCURRENT-MF: concurrent POSTs for same scheme both return 200; one holding remains."""
    user = merge_seed["user"]
    client = api.as_user(user)

    r1, r2 = await asyncio.gather(
        client.post("/assets", json=_MF_PAYLOAD),
        client.post("/assets", json=_MF_PAYLOAD),
    )

    assert r1.status_code == 200, f"r1 failed: {r1.text}"
    assert r2.status_code == 200, f"r2 failed: {r2.text}"

    async with admin_engine.connect() as conn:
        asset_count = await _count(conn, "assets", user)
        holding_count = await _count(conn, "mutual_fund_holdings", user)

    assert asset_count == 1, f"expected 1 asset row, found {asset_count}"
    assert holding_count == 1, f"expected 1 MF holding, found {holding_count}"
