"""Integration-tier fixtures: an ephemeral Postgres with the real schema.

A session-scoped container is provisioned exactly like production: the least-
privilege `app_user` role is created, then `alembic upgrade head` runs as admin
with TLS off (DB_SSL="") to build the tables, grants, and FKs. The FastAPI app is
wired to the container by monkeypatching the request-path engine + session factory,
so the production `get_session` path is exercised unchanged; only identity
(`get_current_user_id`) is overridden per test. Tenant isolation is enforced solely
at the app layer (WHERE user_id = ...) — RLS was removed under architecture-002
Phase 2 (single-user model).
"""
import asyncio
import os
import subprocess
import sys
import uuid

import asyncpg
import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY = sys.executable

USER_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

# Truncate order is irrelevant with CASCADE; assets last for readability.
_TABLES = (
    "transactions", "valuation_history", "crypto_holdings", "fixed_income_holdings",
    "mutual_fund_holdings", "manual_holdings", "portfolio_snapshots", "ai_insights", "assets",
)


@pytest.fixture(scope="session")
def pg():
    with PostgresContainer("postgres:16") as c:
        host = c.get_container_host_ip()
        port = int(c.get_exposed_port(5432))
        su, pw, db = c.username, c.password, c.dbname
        super_url = f"postgresql+asyncpg://{su}:{pw}@{host}:{port}/{db}"
        app_url = f"postgresql+asyncpg://app_user:app_pass@{host}:{port}/{db}"

        async def _create_role():
            conn = await asyncpg.connect(host=host, port=port, user=su, password=pw, database=db)
            await conn.execute("CREATE ROLE app_user LOGIN PASSWORD 'app_pass' NOINHERIT")
            await conn.close()

        asyncio.run(_create_role())

        env = {
            **os.environ,
            "ADMIN_DATABASE_URL": super_url, "DATABASE_URL": app_url, "DB_SSL": "",
        }
        r = subprocess.run([PY, "-m", "alembic", "upgrade", "head"], cwd=BACKEND,
                           env=env, capture_output=True, text=True)
        assert r.returncode == 0, f"alembic failed:\n{r.stdout}\n{r.stderr}"

        yield {"super_url": super_url, "app_url": app_url}


@pytest_asyncio.fixture
async def admin_engine(pg):
    eng = create_async_engine(pg["super_url"], connect_args={})  # superuser, bypasses RLS
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def app_engine(pg):
    eng = create_async_engine(pg["app_url"], connect_args={})  # app_user, subject to RLS
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def seed(admin_engine):
    """Truncate + insert two tenants with distinct, identifiable rows."""
    rows = {"A": {"user": USER_A, "invested": 1000, "current": 1500},
            "B": {"user": USER_B, "invested": 9999, "current": 8888}}
    async with admin_engine.begin() as conn:
        await conn.execute(sa.text(f"TRUNCATE {', '.join(_TABLES)} CASCADE"))
        for label, d in rows.items():
            aid = uuid.uuid4()
            d["asset"] = aid
            p = {"id": aid, "uid": d["user"], "name": f"coin-{label}",
                 "cg": f"coin-{label.lower()}", "sym": label,
                 "inv": d["invested"], "cur": d["current"],
                 "pnl": d["current"] - d["invested"]}
            await conn.execute(sa.text(
                "INSERT INTO assets (id,user_id,name,asset_type,category,liquidity_tier) "
                "VALUES (:id,:uid,:name,'CRYPTO','Crypto','liquid')"), p)
            await conn.execute(sa.text(
                "INSERT INTO crypto_holdings (asset_id,user_id,coingecko_id,symbol,quantity,avg_buy_price) "
                "VALUES (:id,:uid,:cg,:sym,1,:inv)"), p)
            await conn.execute(sa.text(
                "INSERT INTO transactions (id,user_id,asset_id,transaction_type,transaction_date,amount,units,price_per_unit) "
                "VALUES (gen_random_uuid(),:uid,:id,'BUY',CURRENT_DATE,:inv,1,:inv)"), p)
            await conn.execute(sa.text(
                "INSERT INTO valuation_history (id,user_id,asset_id,valuation_date,invested_amount,current_value,pnl,source) "
                "VALUES (gen_random_uuid(),:uid,:id,CURRENT_DATE,:inv,:cur,:pnl,'test')"), p)
            await conn.execute(sa.text(
                "INSERT INTO portfolio_snapshots (id,user_id,snapshot_date,total_invested,total_value,total_pnl,allocation,liquidity,metrics) "
                "VALUES (gen_random_uuid(),:uid,CURRENT_DATE,:inv,:cur,:pnl,'{}'::json,'{}'::json,'{}'::json)"), p)
    return rows


@pytest_asyncio.fixture
async def api(app_engine, monkeypatch):
    """An AsyncClient over the real app, wired to the app_user engine. Switch the
    acting tenant with `api.as_user(uuid)`."""
    import app.api.deps as deps
    import app.db.session as dbs
    from app.core.auth import get_current_user_id
    from app.main import app

    monkeypatch.setattr(dbs, "engine", app_engine)
    monkeypatch.setattr(deps, "AsyncSessionLocal", async_sessionmaker(app_engine, expire_on_commit=False))

    state = {"user": None}
    app.dependency_overrides[get_current_user_id] = lambda: state["user"]
    transport = ASGITransport(app=app, raise_app_exceptions=False)  # return 500s like a real client
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        def as_user(user_id):
            state["user"] = user_id
            return client
        client.as_user = as_user
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def anon_client():
    """Client with no identity override — exercises the real auth gate (401 path)."""
    from app.main import app
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
