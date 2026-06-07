"""Unit tests for CSV import parsing and validation — F4."""
import pytest
from decimal import Decimal

from app.services.importer import parse_and_validate, ROW_LIMIT, SIZE_LIMIT

pytestmark = pytest.mark.unit

HEADER = "transaction_date,asset_type,asset_name,transaction_type,amount,units,price_per_unit,coingecko_id,scheme_code\n"


def csv_bytes(*rows: str) -> bytes:
    return (HEADER + "\n".join(rows) + "\n").encode()


# ── File-level validation ──────────────────────────────────────────────────

def test_rejects_oversized_file():
    content = b"x" * (SIZE_LIMIT + 1)
    with pytest.raises(ValueError, match="exceeds"):
        parse_and_validate(content)


def test_rejects_missing_required_column():
    content = b"transaction_date,asset_type,asset_name,transaction_type\n2022-01-01,CRYPTO,BTC,BUY\n"
    with pytest.raises(ValueError, match="Missing required columns"):
        parse_and_validate(content)


def test_rejects_empty_csv():
    content = HEADER.encode()
    with pytest.raises(ValueError, match="no data rows"):
        parse_and_validate(content)


def test_rejects_over_row_limit():
    rows = "\n".join(
        f"2022-01-01,CRYPTO,Bitcoin,BUY,46000,0.005,9200000,bitcoin,"
        for _ in range(ROW_LIMIT + 1)
    )
    content = (HEADER + rows + "\n").encode()
    with pytest.raises(ValueError, match="row limit"):
        parse_and_validate(content)


# ── Valid rows ─────────────────────────────────────────────────────────────

def test_valid_crypto_row():
    content = csv_bytes("2022-01-15,CRYPTO,Bitcoin,BUY,46000,0.005,9200000,bitcoin,")
    rows, errors = parse_and_validate(content)
    assert len(rows) == 1
    assert errors == []
    r = rows[0]
    assert r.asset_type == "CRYPTO"
    assert r.coingecko_id == "bitcoin"
    assert r.amount == Decimal("46000")
    assert r.units == Decimal("0.005")


def test_valid_mutual_fund_row():
    content = csv_bytes("2022-02-01,MUTUAL_FUND,PPFAS Flexi Cap,BUY,5000,12.5,400,,120503")
    rows, errors = parse_and_validate(content)
    assert len(rows) == 1
    assert errors == []
    r = rows[0]
    assert r.scheme_code == "120503"
    assert r.units == Decimal("12.5")


def test_valid_fi_row():
    content = csv_bytes("2021-04-10,FD,SBI FD,DEPOSIT,100000,,,,")
    rows, errors = parse_and_validate(content)
    assert len(rows) == 1
    assert errors == []
    assert rows[0].asset_type == "FD"


def test_amount_with_indian_comma_formatting():
    content = csv_bytes("2022-01-15,CRYPTO,Bitcoin,BUY,\"1,23,456\",0.005,9200000,bitcoin,")
    rows, errors = parse_and_validate(content)
    assert len(rows) == 1
    assert rows[0].amount == Decimal("123456")


# ── Row-level errors ───────────────────────────────────────────────────────

def test_invalid_date_format():
    content = csv_bytes("15-01-2022,CRYPTO,Bitcoin,BUY,46000,0.005,9200000,bitcoin,")
    rows, errors = parse_and_validate(content)
    assert len(rows) == 0
    assert len(errors) == 1
    assert "invalid date" in errors[0]["errors"][0]


def test_invalid_asset_type():
    content = csv_bytes("2022-01-15,STOCK,Apple,BUY,46000,,,, ")
    rows, errors = parse_and_validate(content)
    assert len(errors) == 1
    assert "invalid asset_type" in errors[0]["errors"][0]


def test_invalid_transaction_type():
    content = csv_bytes("2022-01-15,CRYPTO,Bitcoin,TRANSFER,46000,0.005,9200000,bitcoin,")
    rows, errors = parse_and_validate(content)
    assert len(errors) == 1
    assert "invalid transaction_type" in errors[0]["errors"][0]


def test_zero_amount_rejected():
    content = csv_bytes("2022-01-15,CRYPTO,Bitcoin,BUY,0,0.005,9200000,bitcoin,")
    rows, errors = parse_and_validate(content)
    assert len(errors) == 1
    assert "amount must be greater than zero" in errors[0]["errors"][0]


def test_crypto_missing_coingecko_id():
    content = csv_bytes("2022-01-15,CRYPTO,Bitcoin,BUY,46000,0.005,9200000,,")
    rows, errors = parse_and_validate(content)
    assert len(errors) == 1
    assert any("coingecko_id" in e for e in errors[0]["errors"])


def test_mf_missing_scheme_code():
    content = csv_bytes("2022-02-01,MUTUAL_FUND,PPFAS,BUY,5000,12.5,400,,")
    rows, errors = parse_and_validate(content)
    assert len(errors) == 1
    assert any("scheme_code" in e for e in errors[0]["errors"])


def test_mixed_valid_and_invalid_rows():
    content = csv_bytes(
        "2022-01-15,CRYPTO,Bitcoin,BUY,46000,0.005,9200000,bitcoin,",  # valid
        "bad-date,CRYPTO,Bitcoin,BUY,46000,0.005,9200000,bitcoin,",    # invalid date
        "2022-02-01,MUTUAL_FUND,PPFAS,BUY,5000,12.5,400,,120503",      # valid
    )
    rows, errors = parse_and_validate(content)
    assert len(rows) == 2
    assert len(errors) == 1
    assert errors[0]["row_num"] == 3   # second data row = row 3 (header is row 1)


def test_preview_serialisation():
    content = csv_bytes("2022-01-15,CRYPTO,Bitcoin,BUY,46000,0.005,9200000,bitcoin,")
    rows, _ = parse_and_validate(content)
    preview = rows[0].to_preview()
    assert preview["asset_type"] == "CRYPTO"
    assert preview["amount"] == 46000.0
    assert preview["row_num"] == 2
