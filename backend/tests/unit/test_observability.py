"""Unit tests for log redaction (A8)."""
import pytest

from app.core.observability import redact

pytestmark = pytest.mark.unit


def test_redacts_dsn_credentials():
    out = redact("could not connect: postgresql+asyncpg://app_user:s3cr3t@db.host:5432/postgres")
    assert "s3cr3t" not in out
    assert "://***:***@db.host" in out


def test_redacts_jwt():
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV"
    out = redact(f"bad token {token}")
    assert "eyJhbGci" not in out
    assert "***JWT***" in out


def test_leaves_benign_text_unchanged():
    msg = "valuation recalculation failed for asset 123 (timeout after 10s)"
    assert redact(msg) == msg
