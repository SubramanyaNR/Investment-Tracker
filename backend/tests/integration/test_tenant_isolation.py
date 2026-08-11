"""Two-tenant isolation through the real app (app_user engine, app-layer filtering).

Reproduces SECURITY-AUDIT §5 (each tenant sees only its own data) and §4 (no IDOR:
a tenant cannot target another's asset). Identity is injected; every query runs as
app_user and is scoped by an explicit WHERE user_id clause — the sole enforcement
mechanism since RLS was removed under architecture-002 Phase 2 (single-user model).
"""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_asset_list_scoped_to_owner(api, seed):
    a = (await api.as_user(seed["A"]["user"]).get("/assets")).json()["items"]
    b = (await api.as_user(seed["B"]["user"]).get("/assets")).json()["items"]
    a_ids = {x["id"] for x in a}
    b_ids = {x["id"] for x in b}
    assert a_ids == {str(seed["A"]["asset"])}
    assert b_ids == {str(seed["B"]["asset"])}
    assert a_ids.isdisjoint(b_ids)


async def test_dashboard_totals_scoped_to_owner(api, seed):
    a = (await api.as_user(seed["A"]["user"]).get("/dashboard")).json()
    b = (await api.as_user(seed["B"]["user"]).get("/dashboard")).json()
    assert a["total_invested"] == seed["A"]["invested"]   # 1000, not B's 9999
    assert b["total_invested"] == seed["B"]["invested"]


async def test_transactions_scoped_to_owner(api, seed):
    resp = (await api.as_user(seed["A"]["user"]).get("/transactions")).json()
    a = resp["items"]
    assert a and all(t["asset_id"] == str(seed["A"]["asset"]) for t in a)
    assert str(seed["B"]["asset"]) not in {t["asset_id"] for t in a}


async def test_valuations_scoped_to_owner(api, seed):
    a = (await api.as_user(seed["A"]["user"]).get("/valuations/latest")).json()
    assert {v["asset_id"] for v in a} == {str(seed["A"]["asset"])}


async def test_snapshots_scoped_to_owner(api, seed):
    a = (await api.as_user(seed["A"]["user"]).get("/snapshots")).json()
    b = (await api.as_user(seed["B"]["user"]).get("/snapshots")).json()
    assert [s["total_invested"] for s in a] == [seed["A"]["invested"]]
    assert [s["total_invested"] for s in b] == [seed["B"]["invested"]]


async def test_cannot_delete_other_tenants_asset(api, seed):
    # A targets B's asset id -> 404 (not found in A's tenant), no existence leak.
    resp = await api.as_user(seed["A"]["user"]).delete(f"/assets/{seed['B']['asset']}")
    assert resp.status_code == 404
    # B's asset still present for B.
    b = (await api.as_user(seed["B"]["user"]).get("/assets")).json()["items"]
    assert {x["id"] for x in b} == {str(seed["B"]["asset"])}


async def test_cannot_sell_other_tenants_crypto(api, seed):
    resp = await api.as_user(seed["A"]["user"]).post(
        f"/assets/{seed['B']['asset']}/sell-crypto", json={"quantity": 1})
    assert resp.status_code == 404


async def test_can_delete_own_asset(api, seed):
    resp = await api.as_user(seed["A"]["user"]).delete(f"/assets/{seed['A']['asset']}")
    assert resp.status_code in (200, 204)
    after = (await api.as_user(seed["A"]["user"]).get("/assets")).json()
    assert after["items"] == [] and after["total"] == 0
