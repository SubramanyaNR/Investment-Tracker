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

async def _expect_401(token):
    with pytest.raises(HTTPException) as ei:
        await get_current_user_id(access_token=token)
    assert ei.value.status_code == 401


async def test_valid_access_token_returns_sub():
    token = create_access_token(VALID_SUB)
    assert await get_current_user_id(access_token=token) == VALID_SUB


async def test_missing_cookie_401():
    await _expect_401(None)


async def test_expired_token_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": str(VALID_SUB), "iat": now, "exp": now - datetime.timedelta(seconds=1)}
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    await _expect_401(token)


async def test_missing_sub_401():
    now = datetime.datetime.now(UTC)
    claims = {"iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    await _expect_401(token)


async def test_non_uuid_sub_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": "not-a-uuid", "iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    await _expect_401(token)


async def test_wrong_secret_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": str(VALID_SUB), "iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, "a-completely-different-secret", algorithm="HS256")
    await _expect_401(token)


async def test_alg_none_401():
    now = datetime.datetime.now(UTC)
    claims = {"sub": str(VALID_SUB), "iat": now, "exp": now + datetime.timedelta(hours=1)}
    token = jwt.encode(claims, "", algorithm="none")
    await _expect_401(token)


async def test_tampered_payload_401():
    token = create_access_token(VALID_SUB)
    head, payload, sig = token.split(".")
    payload = ("A" if payload[0] != "A" else "B") + payload[1:]
    await _expect_401(f"{head}.{payload}.{sig}")


async def test_malformed_token_401():
    await _expect_401("not.a.valid.jwt")


async def test_old_supabase_style_es256_token_rejected():
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
    await _expect_401(token)


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


# ── AUTH_ENABLED=false bypass (secure-001 / feature-020) ────────────────────
# get_current_user_id must always resolve to the one bootstrapped admin user
# when auth is disabled — never null, never whatever the caller supplies.

BOOTSTRAPPED_ADMIN = uuid.UUID("99999999-9999-9999-9999-999999999999")


class _FakeAdminResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeAdminSession:
    def __init__(self, row):
        self._row = row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def execute(self, *_args, **_kwargs):
        return _FakeAdminResult(self._row)


@pytest.fixture(autouse=True)
def _reset_disabled_mode_cache():
    """The bypass caches the resolved admin id at module scope — reset it around
    every test in this file so tests don't leak state into each other."""
    auth_module._disabled_mode_admin_id = None
    yield
    auth_module._disabled_mode_admin_id = None


def _patch_admin_session(monkeypatch, row):
    import app.db.session as db_session
    monkeypatch.setattr(db_session, "AdminSessionLocal", lambda: _FakeAdminSession(row))


async def test_auth_disabled_resolves_to_bootstrapped_admin(monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", False)
    _patch_admin_session(monkeypatch, (BOOTSTRAPPED_ADMIN,))
    assert await get_current_user_id(access_token=None) == BOOTSTRAPPED_ADMIN


async def test_auth_disabled_ignores_client_supplied_token(monkeypatch):
    """A forged/valid-looking cookie claiming a different user must be ignored
    entirely — the disabled-mode identity always comes from the DB lookup, never
    from anything the caller sends."""
    monkeypatch.setattr(settings, "auth_enabled", False)
    _patch_admin_session(monkeypatch, (BOOTSTRAPPED_ADMIN,))
    forged = create_access_token(uuid.UUID("22222222-2222-2222-2222-222222222222"))
    assert await get_current_user_id(access_token=forged) == BOOTSTRAPPED_ADMIN


async def test_auth_disabled_no_user_row_raises_500(monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", False)
    _patch_admin_session(monkeypatch, None)
    with pytest.raises(HTTPException) as ei:
        await get_current_user_id(access_token=None)
    assert ei.value.status_code == 500


async def test_auth_disabled_caches_after_first_lookup(monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", False)
    calls = {"n": 0}

    class _CountingSession(_FakeAdminSession):
        async def execute(self, *args, **kwargs):
            calls["n"] += 1
            return await super().execute(*args, **kwargs)

    import app.db.session as db_session
    monkeypatch.setattr(db_session, "AdminSessionLocal", lambda: _CountingSession((BOOTSTRAPPED_ADMIN,)))

    await get_current_user_id(access_token=None)
    await get_current_user_id(access_token=None)
    assert calls["n"] == 1


async def test_auth_enabled_still_requires_valid_token_when_flag_is_false_elsewhere(monkeypatch):
    """Sanity check the flag actually gates the branch: with auth_enabled=True
    (the test-suite default), a missing cookie still 401s exactly as before,
    even though the disabled-mode code path now exists."""
    monkeypatch.setattr(settings, "auth_enabled", True)
    with pytest.raises(HTTPException) as ei:
        await get_current_user_id(access_token=None)
    assert ei.value.status_code == 401
