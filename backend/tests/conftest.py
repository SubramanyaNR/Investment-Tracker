"""Test bootstrap.

Sets hermetic dummy env vars BEFORE any `app.*` module is imported, so `Settings()`
constructs without real secrets and no test touches the database or any external API.
These take precedence over `backend/.env`, so the suite runs identically with or
without a real `.env` present.

Unit tests (A3a) never open a connection — the SQLAlchemy engines are created lazily,
so dummy DSNs are sufficient. A3b adds real ephemeral-Postgres fixtures for the
integration tier.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("ADMIN_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-a-real-secret")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.invalid")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password-not-real")
# AUTH_ENABLED defaults to false in production (secure-001/feature-020), but the
# suite's existing 401/identity tests assume the credential check is active —
# opt in explicitly here so the default-off behavior doesn't silently swallow them.
# Tests for the disabled-auth bypass itself override this per-test.
os.environ.setdefault("AUTH_ENABLED", "true")
