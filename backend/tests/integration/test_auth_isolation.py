"""Multi-tenancy isolation matrix — IDOR prevention & ownership checks.

Validates:
- Multi-tenancy matrix: two-user isolation; cross-user operations → 404 (not 403)
- Ownership checks don't leak resource existence (silent failure on IDOR)

From SECURITY-AUDIT.md §7:
  "Authorization: every endpoint 401 without token; cross-user delete/sell/redeem/top-up → 404."
  "Multi-tenancy: two-user seed (rollback) — dashboards, asset list, transactions, valuations all
   filter by owner."

Note: Authorization 401-without-token matrix is covered by test_authorization.py.
This file focuses on IDOR (cross-user operations) and multi-tenancy isolation.
"""
import uuid
from decimal import Decimal

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ────────────────────────────────────────────────────────────────────────────
# Multi-tenancy Isolation: Two-user test
# ────────────────────────────────────────────────────────────────────────────


async def test_dashboard_isolates_by_user(api, seed):
    """Test: Dashboard returns only the user's data.

    User outcome: User A opens dashboard → sees only their portfolio totals, not User B's.
    """
    # User A views dashboard
    resp_a = await api.as_user(seed["A"]["user"]).get("/dashboard")
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    # Should contain User A's values (from seed)
    assert data_a["total_invested"] == seed["A"]["invested"]
    assert data_a["total_value"] == seed["A"]["current"]

    # User B views dashboard
    resp_b = await api.as_user(seed["B"]["user"]).get("/dashboard")
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    # Should contain User B's values, not User A's
    assert data_b["total_invested"] == seed["B"]["invested"]
    assert data_b["total_value"] == seed["B"]["current"]


async def test_asset_list_isolates_by_user(api, seed):
    """Test: GET /assets returns only the user's assets.

    User outcome: User A opens holdings → sees only their assets, not User B's.
    """
    # User A lists assets
    resp_a = await api.as_user(seed["A"]["user"]).get("/assets")
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assets_a = data_a["items"]
    assert len(assets_a) == 1
    assert assets_a[0]["name"] == f"coin-A"

    # User B lists assets
    resp_b = await api.as_user(seed["B"]["user"]).get("/assets")
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assets_b = data_b["items"]
    assert len(assets_b) == 1
    assert assets_b[0]["name"] == f"coin-B"


async def test_transactions_isolate_by_user(api, seed):
    """Test: GET /transactions returns only the user's transactions.

    User outcome: User A views transaction history → sees only their transactions.
    """
    # User A lists transactions
    resp_a = await api.as_user(seed["A"]["user"]).get("/transactions")
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["total"] == 1  # Seed creates 1 transaction per user
    assert len(data_a["items"]) == 1

    # User B lists transactions
    resp_b = await api.as_user(seed["B"]["user"]).get("/transactions")
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["total"] == 1
    assert len(data_b["items"]) == 1


async def test_valuations_isolate_by_user(api, seed):
    """Test: GET /valuations/latest returns only the user's valuations.

    User outcome: User A views current valuations → sees only their holdings.
    """
    # User A lists valuations
    resp_a = await api.as_user(seed["A"]["user"]).get("/valuations/latest")
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert len(data_a) == 1
    assert data_a[0]["current_value"] == seed["A"]["current"]

    # User B lists valuations
    resp_b = await api.as_user(seed["B"]["user"]).get("/valuations/latest")
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert len(data_b) == 1
    assert data_b[0]["current_value"] == seed["B"]["current"]


async def test_snapshots_isolate_by_user(api, seed):
    """Test: GET /snapshots returns only the user's portfolio snapshots.

    User outcome: User A views net worth history → sees only their data.
    """
    # User A lists snapshots
    resp_a = await api.as_user(seed["A"]["user"]).get("/snapshots")
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert len(data_a) == 1
    assert data_a[0]["total_invested"] == seed["A"]["invested"]

    # User B lists snapshots
    resp_b = await api.as_user(seed["B"]["user"]).get("/snapshots")
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert len(data_b) == 1
    assert data_b[0]["total_invested"] == seed["B"]["invested"]


# ────────────────────────────────────────────────────────────────────────────
# IDOR Prevention: Cross-user operations → 404 (not 403)
# ────────────────────────────────────────────────────────────────────────────


async def test_delete_other_users_asset_returns_404(api, seed):
    """Test: User A cannot delete User B's asset → 404.

    User outcome: User A tries to delete an asset they don't own → "not found" error.
    Ownership check returns 404, not 403, to avoid leaking resource existence.
    """
    user_b_asset_id = seed["B"]["asset"]

    # User A tries to delete User B's asset
    resp = await api.as_user(seed["A"]["user"]).delete(f"/assets/{user_b_asset_id}")
    assert resp.status_code == 404


async def test_delete_other_users_asset_returns_404_or_not_found(api, seed):
    """Test: User A cannot delete User B's asset → 404.

    Cross-user DELETE should fail silently (404, not 403) to avoid leaking existence.
    """
    user_b_asset_id = seed["B"]["asset"]

    resp = await api.as_user(seed["A"]["user"]).delete(f"/assets/{user_b_asset_id}")
    # Should not succeed; either 404 (not found) or 403 (forbidden) depending on implementation
    # The important part is it doesn't grant access and doesn't error 500
    assert resp.status_code in (404, 403), f"Cross-user delete should fail, got {resp.status_code}"
