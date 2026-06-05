"""RLS backstop, exercised at the database boundary as `app_user`.

Independent of any application WHERE clause: a raw app_user connection with no
`app.current_user_id` GUC must see zero rows (fail-closed), and only its own once
the GUC is set. This is the second line of defense the audit (M1/§11) added.
"""
import sqlalchemy as sa
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_no_guc_returns_zero_rows(app_engine, seed):
    async with app_engine.connect() as conn:
        n = await conn.scalar(sa.text("SELECT count(*) FROM assets"))
        assert n == 0  # no app.current_user_id -> NULL -> deny all


async def test_guc_scopes_to_that_tenant(app_engine, seed):
    user_a, user_b = seed["A"]["user"], seed["B"]["user"]
    async with app_engine.connect() as conn:
        await conn.execute(sa.text("SELECT set_config('app.current_user_id', :u, false)"),
                           {"u": str(user_a)})
        assert await conn.scalar(sa.text("SELECT count(*) FROM assets")) == 1
        assert await conn.scalar(sa.text("SELECT user_id FROM assets")) == user_a

        await conn.execute(sa.text("SELECT set_config('app.current_user_id', :u, false)"),
                           {"u": str(user_b)})
        assert await conn.scalar(sa.text("SELECT count(*) FROM assets")) == 1
        assert await conn.scalar(sa.text("SELECT user_id FROM assets")) == user_b


async def test_blank_guc_fails_closed(app_engine, seed):
    # The pooler can leave a stale/empty GUC; NULLIF guards the ::uuid cast -> deny.
    async with app_engine.connect() as conn:
        await conn.execute(sa.text("SELECT set_config('app.current_user_id', '', false)"))
        assert await conn.scalar(sa.text("SELECT count(*) FROM assets")) == 0
