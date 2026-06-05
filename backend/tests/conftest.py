"""Test bootstrap.

Sets hermetic dummy env vars BEFORE any `app.*` module is imported, so `Settings()`
constructs without real secrets and no test touches Supabase, the database, or any
external API. These take precedence over `backend/.env`, so the suite runs identically
with or without a real `.env` present.

Unit tests (A3a) never open a connection — the SQLAlchemy engines and the Supabase
JWKS client are created lazily, so dummy DSNs/URLs are sufficient. A3b will add real
ephemeral-Postgres fixtures here for the integration tier.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("ADMIN_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SUPABASE_JWKS_URL", "https://test.invalid/auth/v1/.well-known/jwks.json")
os.environ.setdefault("SUPABASE_ISSUER", "https://test.invalid/auth/v1")
os.environ.setdefault("SUPABASE_JWT_AUDIENCE", "authenticated")
