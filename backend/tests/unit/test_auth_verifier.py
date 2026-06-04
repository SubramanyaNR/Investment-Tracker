"""AuthN verifier matrix — reproduces SECURITY-AUDIT §3 without touching Supabase.

A locally-generated ES256 keypair is used to mint tokens, and the module's JWKS
client is patched to return the matching public key, so `get_current_user_id`
exercises the real `jwt.decode` path (alg pinning, iss/aud/exp/sub `require`,
signature) offline and deterministically.
"""
import base64
import datetime
import json
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

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


def _creds(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _mint(priv, *, sub=VALID_SUB, iss=None, aud=None, exp_delta=3600, drop=(), alg="ES256"):
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


def test_jwks_failure_becomes_401_not_500(monkeypatch, keypair):
    priv, _ = keypair
    from jwt import PyJWKClientError

    def _boom(token):
        raise PyJWKClientError("simulated JWKS fetch failure")

    monkeypatch.setattr(auth_module._jwk_client, "get_signing_key_from_jwt", _boom)
    _expect_401(_creds(_mint(priv)))
