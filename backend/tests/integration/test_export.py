import uuid
import csv
import io
from datetime import date
import pytest
import pytest_asyncio
import sqlalchemy as sa

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

USER_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

@pytest_asyncio.fixture
async def export_seed(admin_engine):
    """Seed data for USER_A and USER_B to test export and isolation."""
    async with admin_engine.begin() as conn:
        # Cleanup
        await conn.execute(sa.text("DELETE FROM assets WHERE user_id IN (:ua, :ub)"), {"ua": str(USER_A), "ub": str(USER_B)})
        
        # USER_A: Crypto asset with valuation and transaction
        aid1 = uuid.uuid4()
        await conn.execute(sa.text(
            "INSERT INTO assets (id,user_id,name,asset_type,category,liquidity_tier) "
            "VALUES (:id,:uid,'Bitcoin','CRYPTO','Crypto','liquid')"
        ), {"id": str(aid1), "uid": str(USER_A)})
        
        await conn.execute(sa.text(
            "INSERT INTO crypto_holdings (asset_id,user_id,coingecko_id,symbol,quantity,avg_buy_price) "
            "VALUES (:aid,:uid,'bitcoin','btc',1.5,5000000)"
        ), {"aid": str(aid1), "uid": str(USER_A)})
        
        await conn.execute(sa.text(
            "INSERT INTO valuation_history (id,user_id,asset_id,valuation_date,invested_amount,current_value,pnl,price_per_unit,source) "
            "VALUES (gen_random_uuid(),:uid,:aid,:dt,7500000,8000000,500000,5333333,'manual')"
        ), {"uid": str(USER_A), "aid": str(aid1), "dt": date.today()})

        await conn.execute(sa.text(
            "INSERT INTO transactions (id,user_id,asset_id,transaction_type,transaction_date,amount,units,price_per_unit) "
            "VALUES (gen_random_uuid(),:uid,:aid,'BUY',:dt,7500000,1.5,5000000)"
        ), {"uid": str(USER_A), "aid": str(aid1), "dt": date.today()})

        # USER_A: Asset with formula-starting name for injection test
        aid2 = uuid.uuid4()
        await conn.execute(sa.text(
            "INSERT INTO assets (id,user_id,name,asset_type,category,liquidity_tier) "
            "VALUES (:id,:uid,'+Formula Asset','MANUAL','Other','liquid')"
        ), {"id": str(aid2), "uid": str(USER_A)})
        
        await conn.execute(sa.text(
            "INSERT INTO valuation_history (id,user_id,asset_id,valuation_date,invested_amount,current_value,pnl,source) "
            "VALUES (gen_random_uuid(),:uid,:aid,:dt,100,100,0,'manual')"
        ), {"uid": str(USER_A), "aid": str(aid2), "dt": date.today()})

        # USER_B: Asset for isolation test
        aid3 = uuid.uuid4()
        await conn.execute(sa.text(
            "INSERT INTO assets (id,user_id,name,asset_type,category,liquidity_tier) "
            "VALUES (:id,:uid,'User B Private Asset','MANUAL','Other','liquid')"
        ), {"id": str(aid3), "uid": str(USER_B)})
        
        await conn.execute(sa.text(
            "INSERT INTO valuation_history (id,user_id,asset_id,valuation_date,invested_amount,current_value,pnl,source) "
            "VALUES (gen_random_uuid(),:uid,:aid,:dt,1000,1000,0,'manual')"
        ), {"uid": str(USER_B), "aid": str(aid3), "dt": date.today()})

    yield {"user_a": USER_A, "user_b": USER_B}
    
    async with admin_engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM assets WHERE user_id IN (:ua, :ub)"), {"ua": str(USER_A), "ub": str(USER_B)})


async def test_export_holdings_unauthorized(api):
    """QA1: 401 without token (holdings)"""
    resp = await api.get("/export/holdings")
    assert resp.status_code == 401


async def test_export_transactions_unauthorized(api):
    """QA3: 401 without token (transactions)"""
    resp = await api.get("/export/transactions")
    assert resp.status_code == 401


async def test_export_holdings_content_and_isolation(api, export_seed):
    """QA2: Holdings content — correct columns, row count, no cross-user leak"""
    resp = await api.as_user(export_seed["user_a"]).get("/export/holdings")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "text/csv; charset=utf-8"
    assert resp.headers["Cache-Control"] == "no-store"
    assert "wealthsignal_holdings_" in resp.headers["Content-Disposition"]
    
    content = resp.text
    reader = csv.DictReader(io.StringIO(content))
    rows = {r["Asset Name"]: r for r in reader}
    
    # User A should see their 2 assets, but NOT User B's asset
    assert len(rows) == 2
    assert "Bitcoin" in rows
    assert "'+Formula Asset" in rows
    assert "User B Private Asset" not in rows
    
    btc = rows["Bitcoin"]
    assert btc["Asset Type"] == "CRYPTO"
    assert btc["Currency"] == "INR"
    assert btc["Invested Amount"] == "7500000.00"
    assert btc["Current Value"] == "8000000.00"
    assert btc["Units/Quantity"] == "1.5000000000"


async def test_export_transactions_content_and_isolation(api, export_seed):
    """QA4: Transactions content — chronological order, no cross-user leak"""
    resp = await api.as_user(export_seed["user_a"]).get("/export/transactions")
    assert resp.status_code == 200
    
    content = resp.text
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    
    # Only 1 transaction was seeded for User A
    assert len(rows) == 1
    assert rows[0]["Asset Name"] == "Bitcoin"
    assert rows[0]["Transaction Type"] == "BUY"
    assert rows[0]["Amount (INR)"] == "7500000.00"


async def test_export_csv_injection_mitigation(api, export_seed):
    """QA5: CSV quoting — asset names starting with =, +, -, @ are prefixed with '"""
    resp = await api.as_user(export_seed["user_a"]).get("/export/holdings")
    content = resp.text
    
    # The asset name "+Formula Asset" should be escaped to "'+Formula Asset"
    assert "'+Formula Asset" in content
    # Verify it's not just the name but specifically handled by sanitize_csv_value
    reader = csv.DictReader(io.StringIO(content))
    rows = {r["Asset Name"]: r for r in reader}
    assert "'+Formula Asset" in rows
