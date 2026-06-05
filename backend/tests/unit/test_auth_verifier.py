"""AuthN verifier matrix — reproduces SECURITY-AUDIT §3 without touching Supabase.

A locally-generated ES256 keypair is used to mint tokens, and the module's JWKS
client is patched to return the matching public key, so `get_current_user_id`
exercises the real `jwt.decode` path (alg pinning, iss/aud/exp/sub `require`,
signature) offline and deterministically.
"""
import base64
import datetime
import json
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jwt import PyJWKClientConnectionError, PyJWKClientError

from app.core import auth as auth_module
from app.core.auth import get_current_user_id
from app.core.config import settings

pytestmark = pytest.mark.unit
UTC = datetime.timezone.utc
VALID_SUB = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(scope="module")
def keypair():
    priv = ec.generate_private_key(ec.SECP256R1())
    return priv, priv.public_key()


@pytest.fixture(autouse=True)
def _patch_jwks(monkeypatch, keypair):
    _, pub = keypair

    class _Key:
        key = pub

    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", lambda token: _Key())


@pytest.fixture(autouse=True)
def _clear_negative_cache():
    auth_module._negative_cache.clear()
    yield
    auth_module._negative_cache.clear()


def _creds(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _mint(priv, *, sub=VALID_SUB, iss=None, aud=None, exp_delta=3600, drop=(), alg="ES256", kid=None):
    now = datetime.datetime.now(UTC)
    claims = {
        "sub": sub,
        "iss": iss if iss is not None else settings.supabase_issuer,
        "aud": aud if aud is not None else settings.supabase_jwt_audience,
        "iat": now,
        "exp": now + datetime.timedelta(seconds=exp_delta),
    }
    for key in drop:
        claims.pop(key, None)
    if kid is not None:
        return jwt.encode(claims, priv, algorithm=alg, headers={"kid": kid})
    return jwt.encode(claims, priv, algorithm=alg)


def _expect_401(creds):
    with pytest.raises(HTTPException) as ei:
        get_current_user_id(credentials=creds)
    assert ei.value.status_code == 401
    assert ei.value.detail in ("Not authenticated", "Invalid or expired token")  # generic, no leak


def test_valid_token_returns_sub(keypair):
    priv, _ = keypair
    assert get_current_user_id(credentials=_creds(_mint(priv))) == uuid.UUID(VALID_SUB)


def test_missing_credentials_401():
    _expect_401(None)


def test_expired_401(keypair):
    priv, _ = keypair
    _expect_401(_creds(_mint(priv, exp_delta=-10)))


def test_wrong_audience_401(keypair):
    priv, _ = keypair
    _expect_401(_creds(_mint(priv, aud="someone-else")))


def test_wrong_issuer_401(keypair):
    priv, _ = keypair
    _expect_401(_creds(_mint(priv, iss="https://evil.invalid/auth/v1")))


def test_missing_sub_401(keypair):
    priv, _ = keypair
    _expect_401(_creds(_mint(priv, drop=("sub",))))


def test_missing_exp_401(keypair):
    priv, _ = keypair
    _expect_401(_creds(_mint(priv, drop=("exp",))))


def test_non_uuid_sub_401(keypair):
    priv, _ = keypair
    _expect_401(_creds(_mint(priv, sub="not-a-uuid")))


def test_alg_hs256_key_confusion_401(keypair):
    # Attacker signs HS256 with a guessed secret; the verifier pins ES256.
    now = datetime.datetime.now(UTC)
    claims = {
        "sub": VALID_SUB,
        "iss": settings.supabase_issuer,
        "aud": settings.supabase_jwt_audience,
        "iat": now,
        "exp": now + datetime.timedelta(hours=1),
    }
    token = jwt.encode(claims, "guessed-secret-padded-to-32-bytes-min", algorithm="HS256")
    _expect_401(_creds(token))


def test_alg_none_401():
    now = datetime.datetime.now(UTC)
    header = {"alg": "none", "typ": "JWT"}
    payload = {
        "sub": VALID_SUB,
        "iss": settings.supabase_issuer,
        "aud": settings.supabase_jwt_audience,
        "exp": int((now + datetime.timedelta(hours=1)).timestamp()),
    }

    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    _expect_401(_creds(f"{b64(header)}.{b64(payload)}."))


def test_tampered_payload_401(keypair):
    priv, _ = keypair
    head, payload, sig = _mint(priv).split(".")
    payload = ("A" if payload[0] != "A" else "B") + payload[1:]
    _expect_401(_creds(f"{head}.{payload}.{sig}"))


def test_malformed_token_401():
    _expect_401(_creds("not.a.valid.jwt"))


def test_jwks_connection_failure_becomes_401_not_500(monkeypatch, keypair):
    priv, _ = keypair

    def _boom(token):
        raise PyJWKClientConnectionError("simulated Supabase JWKS connection failure")

    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _boom)
    _expect_401(_creds(_mint(priv)))


# ── A9: negative cache tests ─────────────────────────────────────────────────

def test_unknown_kid_cached_after_first_miss(monkeypatch, keypair):
    """Second request with the same bad kid bypasses the JWKS client entirely."""
    priv, _ = keypair
    token = _mint(priv, kid="bad-kid-1234")
    call_count = 0

    def _raise(t):
        nonlocal call_count
        call_count += 1
        raise PyJWKClientError("no matching key")

    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)

    _expect_401(_creds(token))
    assert call_count == 1, "first call must reach JWKS client"

    _expect_401(_creds(token))
    assert call_count == 1, "second call must be short-circuited by negative cache"


def test_negative_cache_hit_still_returns_401(monkeypatch, keypair):
    """A negative cache hit is an auth rejection, not a 500."""
    priv, _ = keypair
    token = _mint(priv, kid="bad-kid-401-check")

    def _raise(t):
        raise PyJWKClientError("no key")

    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
    _expect_401(_creds(token))  # populate
    _expect_401(_creds(token))  # served from cache — still 401


def test_negative_cache_hit_emits_structured_log(monkeypatch, keypair):
    """auth.negative_cache.hit event is logged on a cache hit."""
    priv, _ = keypair
    token = _mint(priv, kid="logged-kid-xyz")
    logged: list[tuple] = []

    def _raise(t):
        raise PyJWKClientError("no key")

    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
    monkeypatch.setattr(auth_module, "log_event", lambda event, **kw: logged.append((event, kw)))

    _expect_401(_creds(token))  # populate cache
    _expect_401(_creds(token))  # cache hit → log emitted

    hits = [(e, kw) for e, kw in logged if e == "auth.negative_cache.hit"]
    assert len(hits) == 1
    assert hits[0][1]["kid"] == "logged-k"  # truncated to 8 chars


def test_negative_cache_log_does_not_leak_full_kid(monkeypatch, keypair):
    """The full kid value is never written to the log."""
    priv, _ = keypair
    long_kid = "a" * 64
    token = _mint(priv, kid=long_kid)
    logged: list[tuple] = []

    def _raise(t):
        raise PyJWKClientError("no key")

    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
    monkeypatch.setattr(auth_module, "log_event", lambda event, **kw: logged.append((event, kw)))

    _expect_401(_creds(token))  # populate
    _expect_401(_creds(token))  # cache hit

    for event, kw in logged:
        if event == "auth.negative_cache.hit":
            assert long_kid not in kw.get("kid", "")


def test_negative_cache_entry_expires(monkeypatch, keypair):
    """An expired negative cache entry allows the JWKS client to be called again."""
    priv, _ = keypair
    token = _mint(priv, kid="expiring-kid")
    call_count = 0

    def _raise(t):
        nonlocal call_count
        call_count += 1
        raise PyJWKClientError("no key")

    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)

    _expect_401(_creds(token))
    assert call_count == 1

    # Manually expire the cache entry
    auth_module._negative_cache["expiring-kid"] = time.monotonic() - 1

    _expect_401(_creds(token))  # cache miss (expired) → JWKS client called again
    assert call_count == 2


def test_valid_kid_not_added_to_negative_cache(keypair):
    """Successful authentication must not populate the negative cache."""
    priv, _ = keypair
    token = _mint(priv, kid="valid-kid-ok")
    result = get_current_user_id(credentials=_creds(token))
    assert result == uuid.UUID(VALID_SUB)
    assert "valid-kid-ok" not in auth_module._negative_cache


def test_connection_error_does_not_populate_negative_cache(monkeypatch, keypair):
    """A transient JWKS network failure must not blacklist a potentially valid kid."""
    priv, _ = keypair
    token = _mint(priv, kid="maybe-valid-kid")

    def _raise(t):
        raise PyJWKClientConnectionError("Supabase unreachable")

    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
    _expect_401(_creds(token))
    assert "maybe-valid-kid" not in auth_module._negative_cache


def test_empty_kid_not_cached_negatively(monkeypatch, keypair):
    """Tokens with no kid field use kid='' which must never enter the negative cache."""
    priv, _ = keypair
    token = _mint(priv)  # no kid header — matches all existing test tokens

    def _raise(t):
        raise PyJWKClientError("no key")

    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
    _expect_401(_creds(token))
    assert "" not in auth_module._negative_cache


def test_negative_cache_maxsize_respected(monkeypatch, keypair):
    """Cache never exceeds jwks_negative_cache_maxsize entries."""
    for i in range(settings.jwks_negative_cache_maxsize):
        auth_module._negative_cache[f"fill-kid-{i}"] = time.monotonic() + 60

    priv, _ = keypair
    token = _mint(priv, kid="overflow-kid")

    def _raise(t):
        raise PyJWKClientError("no key")

    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _raise)
    _expect_401(_creds(token))
    assert len(auth_module._negative_cache) == settings.jwks_negative_cache_maxsize
