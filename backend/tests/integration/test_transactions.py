"""Integration tests for paginated GET /transactions — A11.

AC1: response is a {items, total, limit, offset} envelope.
AC2: limit and offset params are honoured.
AC3: limit > 200 returns 422.
AC4: total matches actual DB row count.
"""
import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
import sqlalchemy as sa

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

USER_E = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")


@pytest_asyncio.fixture
async def tx_seed(admin_engine):
    """USER_E with 3 transactions on consecutive dates for deterministic ordering."""
    aid = uuid.uuid4()
    today = date.today()
    async with admin_engine.begin() as conn:
        await conn.execute(
            sa.text("DELETE FROM assets WHERE user_id = :uid"), {"uid": str(USER_E)}
        )
        await conn.execute(
            sa.text(
                "INSERT INTO assets (id,user_id,name,asset_type,category,liquidity_tier) "
                "VALUES (:id,:uid,'tx-test','CRYPTO','Crypto','liquid')"
            ),
            {"id": str(aid), "uid": str(USER_E)},
        )
        for i in range(3):
            await conn.execute(
                sa.text(
                    "INSERT INTO transactions "
                    "(id,user_id,asset_id,transaction_type,transaction_date,amount) "
                    "VALUES (gen_random_uuid(),:uid,:aid,'BUY',:dt,100)"
                ),
                {"uid": str(USER_E), "aid": str(aid), "dt": today - timedelta(days=i)},
            )
    yield {"user": USER_E, "asset": aid, "count": 3}
    async with admin_engine.begin() as conn:
        await conn.execute(
            sa.text("DELETE FROM assets WHERE user_id = :uid"), {"uid": str(USER_E)}
        )


async def test_transactions_default_page(api, tx_seed):
    """AC1: response is paginated envelope with correct default fields."""
    resp = (await api.as_user(tx_seed["user"]).get("/transactions")).json()
    assert set(resp.keys()) == {"items", "total", "limit", "offset"}
    assert resp["limit"] == 50
    assert resp["offset"] == 0
    assert isinstance(resp["items"], list)
    assert isinstance(resp["total"], int)


async def test_transactions_limit_respected(api, tx_seed):
    """AC2: limit param caps items returned; total still reflects full count."""
    resp = (await api.as_user(tx_seed["user"]).get("/transactions?limit=2")).json()
    assert len(resp["items"]) == 2
    assert resp["limit"] == 2
    assert resp["total"] == tx_seed["count"]


async def test_transactions_offset(api, tx_seed):
    """AC2: offset skips rows; page 0 and page 1 return distinct records."""
    r0 = (await api.as_user(tx_seed["user"]).get("/transactions?limit=1&offset=0")).json()
    r1 = (await api.as_user(tx_seed["user"]).get("/transactions?limit=1&offset=1")).json()
    assert len(r0["items"]) == 1
    assert len(r1["items"]) == 1
    assert r0["items"][0]["id"] != r1["items"][0]["id"]


async def test_transactions_total_matches_db(api, tx_seed, admin_engine):
    """AC4: total in response equals actual row count in the database."""
    resp = (await api.as_user(tx_seed["user"]).get("/transactions?limit=1")).json()
    async with admin_engine.connect() as conn:
        row = await conn.execute(
            sa.text("SELECT COUNT(*) FROM transactions WHERE user_id = :uid"),
            {"uid": str(tx_seed["user"])},
        )
        db_count = row.scalar()
    assert resp["total"] == db_count == tx_seed["count"]


async def test_transactions_max_limit_enforced(api, tx_seed):
    """AC3: limit > 200 is rejected with 422 by FastAPI query validation."""
    resp = await api.as_user(tx_seed["user"]).get("/transactions?limit=201")
    assert resp.status_code == 422
