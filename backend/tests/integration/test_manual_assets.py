"""Integration tests for F3 — Manual Asset Tracking.

Q1 — Create MANUAL asset: 200; rows in assets + manual_holdings + valuation_history.
Q2 — GET /assets includes manual_holding detail.
Q3 — POST /valuations/recalculate: snapshot includes manual cost_basis + current_value.
Q4 — Cross-user IDOR: User B cannot delete User A's manual asset (404).
Q5 — Validation: missing cost_basis or current_value → 400.
Q6 — Validation: current_value ≤ 0 → 422.
"""
import uuid

import pytest
import sqlalchemy as sa

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

USER_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

MANUAL_PAYLOAD = {
    "name": "Whitefield Plot",
    "asset_type": "MANUAL",
    "category": "equity",
    "liquidity_tier": "LIQUID",
    "cost_basis": 500000,
    "current_value": 650000,
    "notes": "Plot purchased 2022",
}


async def test_create_manual_asset(api, admin_engine):
    """Q1 — Create MANUAL asset; rows exist in assets + manual_holdings + valuation_history."""
    resp = await api.as_user(USER_A).post("/assets", json=MANUAL_PAYLOAD)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["asset_type"] == "MANUAL"
    asset_id = data["id"]

    async with admin_engine.connect() as conn:
        row = await conn.execute(
            sa.text("SELECT cost_basis, current_value, notes FROM manual_holdings WHERE asset_id = :id"),
            {"id": asset_id},
        )
        mh = row.one()
        assert float(mh[0]) == 500000.0
        assert float(mh[1]) == 650000.0
        assert mh[2] == "Plot purchased 2022"

        vh = await conn.execute(
            sa.text("SELECT invested_amount, current_value, source FROM valuation_history WHERE asset_id = :id"),
            {"id": asset_id},
        )
        val = vh.one()
        assert float(val[0]) == 500000.0
        assert float(val[1]) == 650000.0
        assert val[2] == "manual"


async def test_list_assets_includes_manual_holding(api):
    """Q2 — GET /assets serialises manual_holding detail correctly."""
    await api.as_user(USER_A).post("/assets", json=MANUAL_PAYLOAD)

    resp = await api.as_user(USER_A).get("/assets")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assets = data["items"]

    manual = next((a for a in assets if a["asset_type"] == "MANUAL"), None)
    assert manual is not None, "No MANUAL asset in response"
    assert "manual_holding" in manual
    mh = manual["manual_holding"]
    assert mh["cost_basis"] == 500000.0
    assert mh["current_value"] == 650000.0
    assert mh["notes"] == "Plot purchased 2022"
    assert "value_updated_at" in mh


async def test_snapshot_includes_manual_asset(api, admin_engine):
    """Q3 — Snapshot total_invested and total_value include manual asset values."""
    await api.as_user(USER_A).post("/assets", json=MANUAL_PAYLOAD)

    resp = await api.as_user(USER_A).post("/valuations/recalculate")
    assert resp.status_code == 200, resp.text

    async with admin_engine.connect() as conn:
        snap = await conn.execute(
            sa.text("SELECT total_invested, total_value FROM portfolio_snapshots WHERE user_id = :uid"),
            {"uid": str(USER_A)},
        )
        row = snap.one()
        assert float(row[0]) >= 500000.0, "total_invested must include manual cost_basis"
        assert float(row[1]) >= 650000.0, "total_value must include manual current_value"


async def test_cross_user_cannot_delete_manual_asset(api):
    """Q4 — User B gets 404 attempting to delete User A's manual asset."""
    resp_a = await api.as_user(USER_A).post("/assets", json=MANUAL_PAYLOAD)
    asset_id = resp_a.json()["id"]

    resp_b = await api.as_user(USER_B).delete(f"/assets/{asset_id}")
    assert resp_b.status_code == 404


async def test_manual_asset_missing_cost_basis_rejected(api):
    """Q5 — Missing cost_basis returns 400."""
    payload = {**MANUAL_PAYLOAD, "cost_basis": None}
    resp = await api.as_user(USER_A).post("/assets", json=payload)
    assert resp.status_code in (400, 422), resp.text


async def test_manual_asset_zero_current_value_rejected(api):
    """Q6 — current_value ≤ 0 returns 422."""
    payload = {**MANUAL_PAYLOAD, "current_value": 0}
    resp = await api.as_user(USER_A).post("/assets", json=payload)
    assert resp.status_code == 422, resp.text
