"""Unit tests for the fixed-window limiter + client-IP resolver (A5)."""
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.ratelimit import FixedWindowLimiter, client_ip

pytestmark = pytest.mark.unit


def test_allows_up_to_limit_then_blocks():
    lim = FixedWindowLimiter()
    for _ in range(3):
        assert lim.check("k", 3, 60, now=1000.0)[0] is True
    allowed, retry = lim.check("k", 3, 60, now=1000.0)
    assert allowed is False
    assert retry > 0


def test_window_resets_after_expiry():
    lim = FixedWindowLimiter()
    for _ in range(3):
        lim.check("k", 3, 60, now=1000.0)
    assert lim.check("k", 3, 60, now=1000.0)[0] is False
    assert lim.check("k", 3, 60, now=1061.0)[0] is True  # new window


def test_keys_are_independent():
    lim = FixedWindowLimiter()
    assert lim.check("a", 1, 60, now=1.0)[0] is True
    assert lim.check("a", 1, 60, now=1.0)[0] is False
    assert lim.check("b", 1, 60, now=1.0)[0] is True


def _req(headers=None, host="9.9.9.9"):
    return SimpleNamespace(headers=headers or {}, client=SimpleNamespace(host=host))


def test_client_ip_prefers_leftmost_forwarded_for():
    assert client_ip(_req({"x-forwarded-for": "1.2.3.4, 5.6.7.8"})) == "1.2.3.4"


def test_client_ip_falls_back_to_peer():
    assert client_ip(_req({})) == "9.9.9.9"


def test_client_ip_ignores_xff_when_untrusted(monkeypatch):
    monkeypatch.setattr(settings, "trust_forwarded_for", False)
    assert client_ip(_req({"x-forwarded-for": "1.2.3.4"})) == "9.9.9.9"
