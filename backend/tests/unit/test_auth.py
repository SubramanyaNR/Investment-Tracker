"""Custom auth unit tests (architecture-002 Phase 2) — bcrypt hashing, HS256
access-token verification, CSRF double-submit check. Replaces the old Supabase
JWKS-based test_auth_verifier.py (deleted — that verifier no longer exists)."""
import datetime
import uuid

import jwt
import pytest
from fastapi import HTTPException

from app.core import auth as auth_module
from app.core.auth import (
    create_access_token,
    csrf_check,
    generate_refresh_token,
    get_current_user_id,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.core.config import settings

pytestmark = pytest.mark.unit
UTC = datetime.timezone.utc
VALID_SUB = uuid.UUID("11111111-1111-1111-1111-111111111111")


# ── Password hashing ─────────────────────────────────────────────────────────

def test_hash_and_verify_round_trip():
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h)


def test_verify_rejects_wrong_password():
    h = hash_password("correct horse battery staple")
    assert not verify_password("wrong password", h)


def test_hash_is_not_the_plaintext():
    h = hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"


def test_verify_malformed_hash_fails_closed():
    assert not verify_password("anything", "not-a-real-bcrypt-hash")


# ── Access token (HS256) ──────────────────────────────────────────────────────

def _expect_401(token):
    with pytest.raises(HTTPException) as ei:
        get_current_user_id(access_token=token)
    assert ei.value.status_code == 401


def test_valid_access_token_returns_sub():
    token = create_access_token(VALID_SUB)
    assert get_current_user_id(access_token=token) == VALID_SUB


def test_missing_cookie_401():
    _expect_401(None)


def test_expired_token_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": str(VALID_SUB), "iat": now, "exp": now - datetime.timedelta(seconds=1)}
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    _expect_401(token)


def test_missing_sub_401():
    now = datetime.datetime.now(UTC)
    claims = {"iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    _expect_401(token)


def test_non_uuid_sub_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": "not-a-uuid", "iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    _expect_401(token)


def test_wrong_secret_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": str(VALID_SUB), "iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, "a-completely-different-secret", algorithm="HS256")
    _expect_401(token)


def test_alg_none_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": str(VALID_SUB), "iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, "", algorithm="none")
    _expect_401(token)


def test_tampered_payload_401():
    token = create_access_token(VALID_SUB)
    head, payload, sig = token.split(".")
    payload = ("A" if payload[0] != "A" else "B") + payload[1:]
    _expect_401(f"{head}.{payload}.{sig}")


def test_malformed_token_401():
    _expect_401("not.a.valid.jwt")


def test_old_supabase_style_es256_token_rejected():
    """A token from the old Supabase Auth path (ES256, different issuer/audience
    shape) must not be accepted post-cutover — proves the old path is gone, not
    just that a new one was added alongside it."""
    from cryptography.hazmat.primitives.asymmetric import ec

    priv = ec.generate_private_key(ec.SECP256R1())
    now = datetime.datetime.now(UTC)
    claims = {
        "sub": str(VALID_SUB),
        "iss": "https://old-project.supabase.co/auth/v1",
        "aud": "authenticated",
        "iat": now,
        "exp": now + datetime.timedelta(hours=1),
    }
    token = jwt.encode(claims, priv, algorithm="ES256")
    _expect_401(token)


# ── Refresh token ──────────────────────────────────────────────────────────

def test_refresh_token_hash_is_deterministic():
    raw, token_hash, expires_at = generate_refresh_token()
    assert hash_refresh_token(raw) == token_hash


def test_refresh_token_hash_not_the_raw_value():
    raw, token_hash, _ = generate_refresh_token()
    assert token_hash != raw


def test_refresh_token_expiry_in_future():
    _, _, expires_at = generate_refresh_token()
    assert expires_at > datetime.datetime.now(UTC)


# ── CSRF double-submit ──────────────────────────────────────────────────────
# CSRF only applies to sessions (has_session=True) — an anonymous request has no
# ambient authority to hijack and falls through to the normal 401 auth gate.

def test_csrf_get_request_exempt():
    csrf_check("GET", "/assets", True, None, None)  # no raise


def test_csrf_login_path_exempt():
    csrf_check("POST", "/auth/login", True, None, None)  # no raise


def test_csrf_no_session_exempt():
    # No access_token cookie -> downstream auth gate handles it (401), not CSRF.
    csrf_check("POST", "/assets", False, None, None)  # no raise


def test_csrf_missing_cookie_rejected():
    with pytest.raises(HTTPException) as ei:
        csrf_check("POST", "/assets", True, None, "some-header-value")
    assert ei.value.status_code == 403


def test_csrf_missing_header_rejected():
    with pytest.raises(HTTPException) as ei:
        csrf_check("POST", "/assets", True, "some-cookie-value", None)
    assert ei.value.status_code == 403


def test_csrf_mismatched_values_rejected():
    with pytest.raises(HTTPException) as ei:
        csrf_check("POST", "/assets", True, "cookie-value", "different-header-value")
    assert ei.value.status_code == 403


def test_csrf_matching_values_accepted():
    csrf_check("POST", "/assets", True, "matching-value", "matching-value")  # no raise
