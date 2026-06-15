"""Integration tests for F4 — CSV Transaction Import.

Q1 — dry_run=true: returns preview, no DB writes.
Q2 — dry_run=false: creates assets + transactions + valuation_history.
Q3 — CRYPTO merge: second import into same coingecko_id averages holding.
Q4 — MF merge: second import into same scheme_code averages holding.
Q5 — Mixed valid/invalid: valid rows imported, errors reported.
Q6 — Cross-user isolation: imported assets scoped to JWT user only.
Q7 — Template endpoint: returns CSV with correct content-type.
Q8 — No valid rows: dry_run=false returns 400.
Q9 — Row limit exceeded: returns 400.
"""
import io
import uuid

import pytest
import pytest_asyncio
import sqlalchemy as sa

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

USER_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

_TRUNCATE = (
    "transactions", "valuation_history", "crypto_holdings", "fixed_income_holdings",
    "mutual_fund_holdings", "manual_holdings", "portfolio_snapshots", "ai_insights", "assets",
)


@pytest_asyncio.fixture(autouse=True)
async def clean_db(admin_engine):
    """Truncate all user-data tables and reset rate limiter before each test."""
    from app.core.ratelimit import limiter
    limiter._hits.clear()
    async with admin_engine.begin() as conn:
        await conn.execute(sa.text(f"TRUNCATE {', '.join(_TRUNCATE)} CASCADE"))
    yield

HEADER = (
    "transaction_date,asset_type,asset_name,transaction_type,"
    "amount,units,price_per_unit,coingecko_id,scheme_code\n"
)

CRYPTO_ROW  = "2022-01-15,CRYPTO,Bitcoin,BUY,46000,0.005,9200000,bitcoin,\n"
MF_ROW      = "2022-02-01,MUTUAL_FUND,PPFAS Flexi Cap,BUY,5000,12.5,400,,120503\n"
FI_ROW      = "2021-04-10,FD,SBI Fixed Deposit,DEPOSIT,100000,,,,\n"
INVALID_ROW = "bad-date,CRYPTO,Bitcoin,BUY,46000,0.005,9200000,bitcoin,\n"


def csv_file(*rows: str) -> tuple[bytes, str]:
    content = (HEADER + "".join(rows)).encode()
    return content, "test.csv"


def _upload(content: bytes, filename: str = "test.csv"):
    return {"file": (filename, io.BytesIO(content), "text/csv")}


async def _post_import(api, user, content: bytes, dry_run: bool):
    return await api.as_user(user).post(
        f"/import/csv?dry_run={str(dry_run).lower()}",
        files={"file": ("test.csv", io.BytesIO(content), "text/csv")},
    )


async def test_dry_run_returns_preview_no_db_writes(api, admin_engine):
    """Q1 — dry_run=true: preview returned; no assets or transactions written."""
    content = (HEADER + CRYPTO_ROW).encode()
    resp = await _post_import(api, USER_A, content, dry_run=True)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["dry_run"] is True
    assert data["valid_count"] == 1
    assert data["error_count"] == 0
    assert len(data["preview"]) == 1
    assert data["preview"][0]["asset_type"] == "CRYPTO"

    async with admin_engine.connect() as conn:
        count = await conn.execute(
            sa.text("SELECT COUNT(*) FROM assets WHERE user_id = :uid"), {"uid": str(USER_A)}
        )
        assert count.scalar() == 0, "dry_run must not write to DB"


async def test_confirm_creates_assets_and_transactions(api, admin_engine):
    """Q2 — dry_run=false: assets + transactions + valuation_history written."""
    content = (HEADER + CRYPTO_ROW + FI_ROW).encode()
    resp = await _post_import(api, USER_A, content, dry_run=False)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["transactions_imported"] == 2
    assert data["assets_created"] == 2

    async with admin_engine.connect() as conn:
        assets = await conn.execute(
            sa.text("SELECT COUNT(*) FROM assets WHERE user_id = :uid"), {"uid": str(USER_A)}
        )
        assert assets.scalar() == 2

        txs = await conn.execute(
            sa.text("SELECT COUNT(*) FROM transactions WHERE user_id = :uid"), {"uid": str(USER_A)}
        )
        assert txs.scalar() == 2

        vals = await conn.execute(
            sa.text("SELECT COUNT(*) FROM valuation_history WHERE user_id = :uid"), {"uid": str(USER_A)}
        )
        assert vals.scalar() == 2


async def test_crypto_merges_into_existing_holding(api, admin_engine):
    """Q3 — Two CRYPTO imports with same coingecko_id merge the holding."""
    content = (HEADER + CRYPTO_ROW).encode()
    await _post_import(api, USER_A, content, dry_run=False)

    second_row = "2022-03-01,CRYPTO,Bitcoin,BUY,92000,0.005,18400000,bitcoin,\n"
    content2 = (HEADER + second_row).encode()
    resp = await _post_import(api, USER_A, content2, dry_run=False)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["assets_merged"] == 1
    assert data["assets_created"] == 0

    async with admin_engine.connect() as conn:
        row = await conn.execute(
            sa.text("SELECT quantity FROM crypto_holdings WHERE user_id = :uid"), {"uid": str(USER_A)}
        )
        qty = row.scalar()
        assert abs(float(qty) - 0.01) < 0.0001, f"Expected 0.01 total units, got {qty}"

        asset_count = await conn.execute(
            sa.text("SELECT COUNT(*) FROM assets WHERE user_id = :uid AND asset_type = 'CRYPTO'"),
            {"uid": str(USER_A)},
        )
        assert asset_count.scalar() == 1, "Should still be one CRYPTO asset after merge"


async def test_mf_merges_into_existing_holding(api, admin_engine):
    """Q4 — Two MF imports with same scheme_code merge the holding."""
    content = (HEADER + MF_ROW).encode()
    await _post_import(api, USER_A, content, dry_run=False)

    second_mf = "2022-03-01,MUTUAL_FUND,PPFAS Flexi Cap,BUY,5000,11.9,420,,120503\n"
    content2 = (HEADER + second_mf).encode()
    resp = await _post_import(api, USER_A, content2, dry_run=False)
    assert resp.status_code == 200
    data = resp.json()
    assert data["assets_merged"] == 1

    async with admin_engine.connect() as conn:
        row = await conn.execute(
            sa.text("SELECT units FROM mutual_fund_holdings WHERE user_id = :uid"), {"uid": str(USER_A)}
        )
        total_units = float(row.scalar())
        assert abs(total_units - (12.5 + 11.9)) < 0.001


async def test_mixed_rows_imports_valid_reports_errors(api, admin_engine):
    """Q5 — Valid rows imported; invalid rows returned in errors list."""
    content = (HEADER + CRYPTO_ROW + INVALID_ROW + FI_ROW).encode()
    resp = await _post_import(api, USER_A, content, dry_run=False)
    assert resp.status_code == 200
    data = resp.json()
    assert data["transactions_imported"] == 2   # CRYPTO + FI
    assert data["error_count"] == 1             # INVALID_ROW
    assert data["errors"][0]["row_num"] == 3


async def test_cross_user_isolation(api, admin_engine):
    """Q6 — Assets from User A's import are not visible to User B."""
    content = (HEADER + CRYPTO_ROW).encode()
    await _post_import(api, USER_A, content, dry_run=False)

    resp_b = await api.as_user(USER_B).get("/assets")
    assert resp_b.status_code == 200
    assert resp_b.json()["items"] == [], "User B must see none of User A's imported assets"


async def test_template_download_authenticated(api):
    """Q7a — Authenticated user can download template."""
    resp = await api.as_user(USER_A).get("/import/csv/template")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "transaction_date" in resp.text
    assert "bitcoin" in resp.text


async def test_template_download_anonymous(anon_client):
    """Q7b — Anonymous user (no JWT) can download template. This is the bug fix."""
    resp = await anon_client.get("/import/csv/template")
    assert resp.status_code == 200, f"Expected 200 for public template, got {resp.status_code}: {resp.text}"
    assert "text/csv" in resp.headers["content-type"]
    assert "transaction_date" in resp.text


async def test_import_requires_authentication(anon_client):
    """Q7c — Anonymous POST /import/csv is rejected with 401."""
    content = (HEADER + CRYPTO_ROW).encode()
    resp = await anon_client.post(
        "/import/csv?dry_run=true",
        files={"file": ("test.csv", io.BytesIO(content), "text/csv")},
    )
    assert resp.status_code == 401, f"Expected 401 for unauthenticated import, got {resp.status_code}"


async def test_no_valid_rows_returns_400(api):
    """Q8 — dry_run=false with only invalid rows returns 400."""
    content = (HEADER + INVALID_ROW).encode()
    resp = await _post_import(api, USER_A, content, dry_run=False)
    assert resp.status_code == 400


async def test_row_limit_exceeded_returns_400(api):
    """Q9 — CSV exceeding row limit returns 400 before parsing."""
    from app.services.importer import ROW_LIMIT
    rows = "".join(
        f"2022-01-01,FD,FD {i},DEPOSIT,100000,,,,\n" for i in range(ROW_LIMIT + 1)
    )
    content = (HEADER + rows).encode()
    resp = await _post_import(api, USER_A, content, dry_run=True)
    assert resp.status_code == 400
    assert "row limit" in resp.json()["detail"].lower()
