## Modified Files (git diff HEAD)

```diff
diff --git a/backend/app/api/transactions.py b/backend/app/api/transactions.py
index 99c179e..9b64dfd 100644
--- a/backend/app/api/transactions.py
+++ b/backend/app/api/transactions.py
@@ -1,7 +1,8 @@
 import uuid
-from fastapi import APIRouter, Depends, Query
+from datetime import date
+from fastapi import APIRouter, Depends, Query, HTTPException
 from sqlalchemy import select, func
 from app.api.deps import get_session
 from app.db.models import Transaction, Asset
 from app.core.auth import get_current_user_id
 
@@ -10,22 +11,34 @@ router = APIRouter()
 
 @router.get("/transactions")
 async def list_transactions(
     session=Depends(get_session),
     user_id: uuid.UUID = Depends(get_current_user_id),
+    from_date: date | None = Query(default=None, alias="from"),
+    to_date: date | None = Query(default=None, alias="to"),
     limit: int = Query(default=50, ge=1, le=200),
     offset: int = Query(default=0, ge=0),
 ):
+    if from_date and to_date and from_date > to_date:
+        raise HTTPException(status_code=422, detail="from_date must not be after to_date")
+
+    # Base filter: ownership
+    filters = [Transaction.user_id == user_id]
+    if from_date:
+        filters.append(Transaction.transaction_date >= from_date)
+    if to_date:
+        filters.append(Transaction.transaction_date <= to_date)
+
     total_result = await session.execute(
-        select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)
+        select(func.count()).select_from(Transaction).where(*filters)
     )
     total = total_result.scalar_one()
 
     result = await session.execute(
         select(Transaction, Asset)
         .join(Asset, Transaction.asset_id == Asset.id)
-        .where(Transaction.user_id == user_id)
+        .where(*filters)
         .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
         .limit(limit)
         .offset(offset)
     )
     rows = result.all()
diff --git a/backend/tests/integration/test_transactions.py b/backend/tests/integration/test_transactions.py
index f19f154..6dcef82 100644
--- a/backend/tests/integration/test_transactions.py
+++ b/backend/tests/integration/test_transactions.py
@@ -90,5 +90,92 @@ async def test_transactions_total_matches_db(api, tx_seed, admin_engine):
 
 async def test_transactions_max_limit_enforced(api, tx_seed):
     """AC3: limit > 200 is rejected with 422 by FastAPI query validation."""
     resp = await api.as_user(tx_seed["user"]).get("/transactions?limit=201")
     assert resp.status_code == 422
+
+
+async def test_transactions_date_filter_from(api, tx_seed):
+    """Filter by 'from' date inclusively."""
+    today = date.today()
+    from_date = today - timedelta(days=1)
+    resp = (await api.as_user(tx_seed["user"]).get(f"/transactions?from={from_date}")).json()
+    # tx_seed has today, today-1, today-2.
+    # from today-1 should return today and today-1 (2 items).
+    assert len(resp["items"]) == 2
+    assert all(date.fromisoformat(i["transaction_date"]) >= from_date for i in resp["items"])
+
+
+async def test_transactions_date_filter_to(api, tx_seed):
+    """Filter by 'to' date inclusively."""
+    today = date.today()
+    to_date = today - timedelta(days=1)
+    resp = (await api.as_user(tx_seed["user"]).get(f"/transactions?to={to_date}")).json()
+    # to today-1 should return today-1 and today-2 (2 items).
+    assert len(resp["items"]) == 2
+    assert all(date.fromisoformat(i["transaction_date"]) <= to_date for i in resp["items"])
+
+
+async def test_transactions_date_filter_range(api, tx_seed):
+    """Filter by both 'from' and 'to' dates inclusively."""
+    today = date.today()
+    from_date = today - timedelta(days=1)
+    to_date = today - timedelta(days=1)
+    resp = (
+        await api.as_user(tx_seed["user"]).get(f"/transactions?from={from_date}&to={to_date}")
+    ).json()
+    # from today-1 to today-1 should return exactly today-1 (1 item).
+    assert len(resp["items"]) == 1
+    assert resp["items"][0]["transaction_date"] == str(from_date)
+
+
+async def test_transactions_date_filter_invalid_range(api, tx_seed):
+    """Return 422 if from > to."""
+    today = date.today()
+    resp = await api.as_user(tx_seed["user"]).get(
+        f"/transactions?from={today}&to={today - timedelta(days=1)}"
+    )
+    assert resp.status_code == 422
+    assert "from_date must not be after to_date" in resp.json()["detail"]
+
+
+async def test_transactions_date_filter_invalid_format(api, tx_seed):
+    """Return 422 for invalid date format."""
+    resp = await api.as_user(tx_seed["user"]).get("/transactions?from=not-a-date")
+    assert resp.status_code == 422
+
+
+async def test_transactions_date_filter_isolation(api, tx_seed, admin_engine):
+    """Verify that date filters don't leak other users' data."""
+    other_user = uuid.uuid4()
+    aid = uuid.uuid4()
+    today = date.today()
+
+    # Seed another user with a transaction in the same range
+    async with admin_engine.begin() as conn:
+        await conn.execute(
+            sa.text(
+                "INSERT INTO assets (id,user_id,name,asset_type,category,liquidity_tier) "
+                "VALUES (:id,:uid,'other','CRYPTO','Crypto','liquid')"
+            ),
+            {"id": str(aid), "uid": str(other_user)},
+        )
+        await conn.execute(
+            sa.text(
+                "INSERT INTO transactions (id,user_id,asset_id,transaction_type,transaction_date,amount) "
+                "VALUES (gen_random_uuid(),:uid,:aid,'BUY',:dt,100)"
+            ),
+            {"uid": str(other_user), "aid": str(aid), "dt": today},
+        )
+
+    try:
+        resp = (await api.as_user(tx_seed["user"]).get(f"/transactions?from={today}")).json()
+        # tx_seed user has one transaction on 'today'.
+        # other_user also has one on 'today'.
+        # Result should only have 1 item (the tx_seed user's one).
+        assert len(resp["items"]) == 1
+        assert resp["total"] == 1
+    finally:
+        async with admin_engine.begin() as conn:
+            await conn.execute(
+                sa.text("DELETE FROM assets WHERE user_id = :uid"), {"uid": str(other_user)}
+            )
```

## New File: backend/alembic/versions/62c0aa1dd7cf_add_transaction_date_user_id_index.py

```
"""add transaction date user id index

Revision ID: 62c0aa1dd7cf
Revises: a1b2c3d4e5f6
Create Date: 2026-06-15 12:36:02.578041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62c0aa1dd7cf'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_transactions_user_id_transaction_date",
        "transactions",
        ["user_id", "transaction_date"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_transactions_user_id_transaction_date", table_name="transactions")

```
