import uuid
import pytest
import sqlalchemy as sa
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# Fresh user for onboarding tests — distinct from USER_A/B/C/D
USER_ONBOARD = uuid.UUID("ee000000-0000-0000-0000-0000000000ee")

@pytest.fixture
async def onboarding_seed(admin_engine):
    """Ensure USER_ONBOARD is wiped before/after."""
    async with admin_engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM assets WHERE user_id = :uid"), {"uid": str(USER_ONBOARD)})
        await conn.execute(sa.text("DELETE FROM users WHERE id = :uid"), {"uid": str(USER_ONBOARD)})
    yield {"user_id": USER_ONBOARD}
    async with admin_engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM assets WHERE user_id = :uid"), {"uid": str(USER_ONBOARD)})
        await conn.execute(sa.text("DELETE FROM users WHERE id = :uid"), {"uid": str(USER_ONBOARD)})

async def test_onboarding_eligibility_flow(api: AsyncClient, onboarding_seed):
    user_id = onboarding_seed["user_id"]
    client = api.as_user(user_id)

    # 1. New user (no assets, no user record) -> Eligible
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_onboarding_eligible"] is True

    # 2. Add an asset -> Onboarding completed
    asset_payload = {
        "name": "Onboarding MF",
        "asset_type": "MUTUAL_FUND",
        "category": "Equity",
        "liquidity_tier": "LIQUID",
        "scheme_code": "ONBOARD-MF-1",
        "amount_invested": 1000,
        "nav_at_purchase": 10,
    }
    resp = await client.post("/assets", json=asset_payload)
    assert resp.status_code == 200
    asset_id = resp.json()["id"]

    # 3. Check dashboard again -> Not eligible
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_onboarding_eligible"] is False

    # 4. Delete asset -> Still not eligible (flag persisted in users table)
    resp = await client.delete(f"/assets/{asset_id}")
    assert resp.status_code == 200
    
    # Confirm asset count is 0
    resp = await client.get("/assets")
    assert len(resp.json()) == 0

    # Dashboard should still show NOT eligible because flag is True
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    assert resp.json()["is_onboarding_eligible"] is False
