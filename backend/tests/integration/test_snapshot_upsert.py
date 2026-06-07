"""Integration tests for atomic snapshot upsert — A10a.

Seed: USER_C with one valuation_history row only (no holdings) so that
recalculate_* functions short-circuit and no external API is called.

I1 — Happy path: POST /valuations/recalculate creates a snapshot row.
I2 — Sequential idempotency: two calls produce exactly one row.
I3 — Concurrent race: asyncio.gather fires two requests simultaneously;
     both must return 200 and exactly one row must exist.
"""
import asyncio
import uuid

import pytest
import pytest_asyncio
import sqlalchemy as sa

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

USER_C = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


@pytest_asyncio.fixture
async def recalc_seed(admin_engine):
    """One asset + one valuation row for USER_C. No holding rows → recalculate
    functions all return early; get_dashboard reads the seeded valuation."""
    aid = uuid.uuid4()
    async with admin_engine.begin() as conn:
        # Clean any residue from prior runs (snapshots have no FK to assets).
        await conn.execute(
            sa.text("DELETE FROM portfolio_snapshots WHERE user_id = :uid"),
            {"uid": str(USER_C)},
        )
        await conn.execute(
            sa.text("DELETE FROM assets WHERE user_id = :uid"),
            {"uid": str(USER_C)},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO assets (id, user_id, name, asset_type, category, liquidity_tier) "
                "VALUES (:id, :uid, 'test-c', 'CRYPTO', 'Crypto', 'liquid')"
            ),
            {"id": str(aid), "uid": str(USER_C)},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO valuation_history "
                "(id, user_id, asset_id, valuation_date, invested_amount, current_value, pnl, source) "
                "VALUES (gen_random_uuid(), :uid, :aid, CURRENT_DATE, 5000, 6000, 1000, 'test')"
            ),
            {"uid": str(USER_C), "aid": str(aid)},
        )
    yield {"user": USER_C, "invested": 5000.0, "current": 6000.0}
    async with admin_engine.begin() as conn:
        await conn.execute(
            sa.text("DELETE FROM portfolio_snapshots WHERE user_id = :uid"),
            {"uid": str(USER_C)},
        )
        await conn.execute(
            sa.text("DELETE FROM assets WHERE user_id = :uid"),
            {"uid": str(USER_C)},
        )


async def _snapshot_count(conn, user_id: uuid.UUID) -> int:
    row = await conn.execute(
        sa.text("SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id = :uid"),
        {"uid": str(user_id)},
    )
    return row.scalar()


async def test_recalculate_creates_snapshot(api, recalc_seed, admin_engine):
    """I1 — POST /valuations/recalculate creates exactly one snapshot row."""
    user = recalc_seed["user"]

    resp = await api.as_user(user).post("/valuations/recalculate")
    assert resp.status_code == 200, resp.text

    async with admin_engine.connect() as conn:
        count = await _snapshot_count(conn, user)
    assert count == 1


async def test_sequential_recalculate_is_idempotent(api, recalc_seed, admin_engine):
    """I2 — Two sequential calls produce exactly one row; no IntegrityError."""
    user = recalc_seed["user"]
    client = api.as_user(user)

    r1 = await client.post("/valuations/recalculate")
    r2 = await client.post("/valuations/recalculate")

    assert r1.status_code == 200, f"first call: {r1.text}"
    assert r2.status_code == 200, f"second call: {r2.text}"

    async with admin_engine.connect() as conn:
        count = await _snapshot_count(conn, user)
    assert count == 1, f"expected 1 snapshot row, found {count}"


async def test_concurrent_recalculate_no_integrity_error(api, recalc_seed, admin_engine):
    """I3 — Two concurrent calls via asyncio.gather both return 200; one row exists."""
    user = recalc_seed["user"]
    client = api.as_user(user)

    r1, r2 = await asyncio.gather(
        client.post("/valuations/recalculate"),
        client.post("/valuations/recalculate"),
    )

    assert r1.status_code == 200, f"r1 failed: {r1.text}"
    assert r2.status_code == 200, f"r2 failed: {r2.text}"

    async with admin_engine.connect() as conn:
        count = await _snapshot_count(conn, user)
    assert count == 1, f"expected 1 snapshot row, found {count}"


async def test_snapshot_total_invested_persisted(api, recalc_seed, admin_engine):
    """S1-A — Snapshot includes total_invested field; matches sum of valuations."""
    user = recalc_seed["user"]
    expected_invested = recalc_seed["invested"]

    resp = await api.as_user(user).post("/valuations/recalculate")
    assert resp.status_code == 200, resp.text

    async with admin_engine.connect() as conn:
        row = await conn.execute(
            sa.text("SELECT total_invested, total_value FROM portfolio_snapshots WHERE user_id = :uid"),
            {"uid": str(user)},
        )
        snapshot = row.one()
    assert snapshot[0] == expected_invested, f"total_invested: expected {expected_invested}, got {snapshot[0]}"
    assert snapshot[1] == 6000.0, f"total_value: expected 6000.0, got {snapshot[1]}"
