## Modified Files (git diff HEAD)

```diff
diff --git a/backend/app/api/assets.py b/backend/app/api/assets.py
index 0f923e0..2d3ae7e 100644
--- a/backend/app/api/assets.py
+++ b/backend/app/api/assets.py
@@ -119,18 +119,29 @@ async def _write_initial_valuation(
 
 @router.get("/assets")
 async def list_assets(
     session=Depends(get_session),
     user_id: uuid.UUID = Depends(get_current_user_id),
+    limit: int = Query(default=50, ge=1, le=200),
+    offset: int = Query(default=0, ge=0),
 ):
+    total_result = await session.execute(
+        select(func.count()).select_from(Asset).where(Asset.user_id == user_id)
+    )
+    total = total_result.scalar_one()
+
     result = await session.execute(
-        select(Asset).where(Asset.user_id == user_id).order_by(Asset.created_at.desc())
+        select(Asset)
+        .where(Asset.user_id == user_id)
+        .order_by(Asset.asset_type.asc(), Asset.name.asc())
+        .limit(limit)
+        .offset(offset)
     )
     assets = result.scalars().all()
 
     if not assets:
-        return []
+        return {"items": [], "total": total, "limit": limit, "offset": offset}
 
     asset_ids = [a.id for a in assets]
 
     crypto_result = await session.execute(
         select(CryptoHolding).where(CryptoHolding.asset_id.in_(asset_ids))
@@ -192,11 +203,16 @@ async def list_assets(
                 "value_updated_at": m.value_updated_at.isoformat(),
             }
 
         rows.append(row)
 
-    return rows
+    return {
+        "items": rows,
+        "total": total,
+        "limit": limit,
+        "offset": offset,
+    }
 
 
 @router.post("/assets")
 async def create_asset(
     payload: AssetCreate,
diff --git a/backend/tests/integration/test_auth_isolation.py b/backend/tests/integration/test_auth_isolation.py
index 852e9ed..98f1c69 100644
--- a/backend/tests/integration/test_auth_isolation.py
+++ b/backend/tests/integration/test_auth_isolation.py
@@ -53,18 +53,20 @@ async def test_asset_list_isolates_by_user(api, seed):
     User outcome: User A opens holdings → sees only their assets, not User B's.
     """
     # User A lists assets
     resp_a = await api.as_user(seed["A"]["user"]).get("/assets")
     assert resp_a.status_code == 200
-    assets_a = resp_a.json()
+    data_a = resp_a.json()
+    assets_a = data_a["items"]
     assert len(assets_a) == 1
     assert assets_a[0]["name"] == f"coin-A"
 
     # User B lists assets
     resp_b = await api.as_user(seed["B"]["user"]).get("/assets")
     assert resp_b.status_code == 200
-    assets_b = resp_b.json()
+    data_b = resp_b.json()
+    assets_b = data_b["items"]
     assert len(assets_b) == 1
     assert assets_b[0]["name"] == f"coin-B"
 
 
 async def test_transactions_isolate_by_user(api, seed):
diff --git a/backend/tests/integration/test_manual_assets.py b/backend/tests/integration/test_manual_assets.py
index 6ebabdb..6a50c25 100644
--- a/backend/tests/integration/test_manual_assets.py
+++ b/backend/tests/integration/test_manual_assets.py
@@ -60,11 +60,12 @@ async def test_list_assets_includes_manual_holding(api):
     """Q2 — GET /assets serialises manual_holding detail correctly."""
     await api.as_user(USER_A).post("/assets", json=MANUAL_PAYLOAD)
 
     resp = await api.as_user(USER_A).get("/assets")
     assert resp.status_code == 200, resp.text
-    assets = resp.json()
+    data = resp.json()
+    assets = data["items"]
 
     manual = next((a for a in assets if a["asset_type"] == "MANUAL"), None)
     assert manual is not None, "No MANUAL asset in response"
     assert "manual_holding" in manual
     mh = manual["manual_holding"]
diff --git a/frontend/lib/api.ts b/frontend/lib/api.ts
index 0344cc1..9a41dc3 100644
--- a/frontend/lib/api.ts
+++ b/frontend/lib/api.ts
@@ -213,11 +213,24 @@ export const getDashboard = () => get<{
   total_invested: number;
   total_pnl: number;
   pnl_percent: number;
   is_onboarding_eligible: boolean;
 }>("/dashboard");
-export const getAssets = () => get<Asset[]>("/assets");
+export const getAssets = async (): Promise<Asset[]> => {
+  const firstPage = await get<AssetPage>("/assets?limit=200");
+  let allAssets = [...firstPage.items];
+  let offset = 200;
+
+  // CEO: Cap at 5 pages × 200 = 1000 assets. Keeps existing UX identical.
+  while (allAssets.length < firstPage.total && offset < 1000) {
+    const nextPage = await get<AssetPage>(`/assets?limit=200&offset=${offset}`);
+    if (nextPage.items.length === 0) break;
+    allAssets = [...allAssets, ...nextPage.items];
+    offset += 200;
+  }
+  return allAssets;
+};
 export const getLatestValuations = () => get<Valuation[]>("/valuations/latest");
 export const getSnapshots = () => get<Snapshot[]>("/snapshots");
 export const getTransactions = () => get<TxPage>("/transactions");
 export const getTopCryptos = () => get<CryptoMarket[]>("/market/crypto/top");
 export const getMarketFreshness = () => get<MarketFreshness>("/market/freshness");
```

## New File: backend/tests/integration/test_assets_pagination.py

```
import uuid
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

USER_P = uuid.UUID("pppppppp-pppp-pppp-pppp-pppppppppppp")

@pytest.fixture
async def seed_assets(api):
    # Seed 3 assets for USER_P
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
    """AC2: offset skips rows."""
    # Assets are ordered by asset_type, name.
    # A: CRYPTO, Asset A
    # B: MUTUAL_FUND, Asset B
    # C: SAVINGS_ACC, Asset C
    
    resp0 = await api.as_user(USER_P).get("/assets?limit=1&offset=0")
    resp1 = await api.as_user(USER_P).get("/assets?limit=1&offset=1")
    
    data0 = resp0.json()
    data1 = resp1.json()
    
    assert data0["items"][0]["name"] == "Asset A"
    assert data1["items"][0]["name"] == "Asset B"

async def test_assets_pagination_max_limit(api):
    """AC3: limit > 200 is rejected with 422."""
    resp = await api.as_user(USER_P).get("/assets?limit=201")
    assert resp.status_code == 422

async def test_assets_pagination_ordering(api, seed_assets):
    """Stable sort on asset_type ASC, name ASC."""
    resp = await api.as_user(USER_P).get("/assets")
    data = resp.json()
    names = [a["name"] for a in data["items"]]
    assert names == ["Asset A", "Asset B", "Asset C"]

```
