"""Access + error logging with req_id correlation and redaction (A8)."""
import logging
import uuid

import pytest

from app.core.observability import logger as obs_logger

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.msgs: list[str] = []

    def emit(self, record):
        self.msgs.append(record.getMessage())


async def test_access_log_req_id_matches_response_header(anon_client):
    cap = _Capture()
    obs_logger.addHandler(cap)
    try:
        resp = await anon_client.get("/health")
    finally:
        obs_logger.removeHandler(cap)

    req_id = resp.headers.get("X-Request-Id")
    assert req_id
    assert any(
        "event=request" in m and f"req_id={req_id}" in m and "path=/health" in m and "status=200" in m
        for m in cap.msgs
    )


async def test_unhandled_error_logged_with_req_id_and_redacted(api, monkeypatch):
    import app.api.dashboard as dashboard

    async def _boom(*args, **kwargs):
        raise RuntimeError("fail postgresql://u:s3cr3t@h:5432/db")

    monkeypatch.setattr(dashboard, "get_dashboard", _boom)
    cap = _Capture()
    obs_logger.addHandler(cap)
    try:
        resp = await api.as_user(uuid.uuid4()).get("/dashboard")
    finally:
        obs_logger.removeHandler(cap)

    assert resp.status_code == 500
    errors = [m for m in cap.msgs if "event=error" in m]
    assert errors
    assert "s3cr3t" not in errors[0]
    assert "://***:***@h" in errors[0]
    assert "req_id=" in errors[0]
