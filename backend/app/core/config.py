from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Request-path connection: non-superuser `app_user` role, subject to RLS.
    database_url: str
    # Admin connection: superuser role for migrations + the scheduler (sees all tenants).
    admin_database_url: str
    cors_origins: str = "http://localhost:3000"

    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    mfapi_base_url: str = "https://api.mfapi.in/mf"

    scheduler_enabled: bool = True

    ai_provider: str = "rules"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    # DB TLS mode for asyncpg. Default "require" (Supabase). Set empty to disable
    # for a local non-TLS Postgres (e.g. the integration-test container).
    db_ssl: str | None = "require"

    # ── architecture-002 Phase 2: custom auth (replaces Supabase Auth) ──────
    # High-entropy secret, generated once, never committed. HS256 is the
    # self-hosted-appropriate choice: no external JWKS verifier exists anymore.
    jwt_secret: str
    access_token_ttl_seconds: int = 900        # 15 min
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30  # 30 days
    # First-run bootstrap only — creates the single admin user if `users` is
    # empty. Not read again afterward; safe to leave in .env or remove post-bootstrap.
    admin_email: str
    admin_password: str
    # Cookies must work over plain HTTP out of the box (self-host docker-compose
    # up, and the founder's own plaintext access path) — Secure is opt-in for
    # whoever puts real HTTPS in front (e.g. Tailscale), not a hardcoded default.
    cookie_secure: bool = False
    # Login attempts per IP per window (WINDOW=60s in ratelimit.py) — cheap
    # brute-force insurance now that there's no email-based password reset.
    rl_login_attempts: int = 5

    # ── A5: market caching + rate limiting ──────────────────────────────────
    rate_limit_enabled: bool = True
    # Backend binds 127.0.0.1 (reachable only via the proxy), so a proxy-set
    # X-Forwarded-For is trustworthy for client identification.
    trust_forwarded_for: bool = True
    # Cache TTLs (seconds): crypto moves fast; MF NAV is daily; scheme list ~static.
    cache_ttl_crypto: int = 60
    cache_ttl_nav: int = 300
    cache_ttl_search: int = 3600
    # Rate limits (requests per 60s).
    rl_market_default: int = 60      # /market/crypto/top, /nav (per IP)
    rl_market_search: int = 30       # /market/.../search (per IP)
    rl_user_general: int = 120       # all authenticated routes (per user)
    rl_user_recalculate: int = 10    # /valuations/recalculate (hits upstream)
    rl_user_insights: int = 6        # /insights/refresh (calls Gemini)
    rl_user_import: int = 5          # /import/csv (file parsing + DB writes)
    rl_user_xirr: int = 20           # /xirr (CPU-light but DB-read heavy)
    rl_user_performance: int = 30    # /performance/* (lightweight DB reads)

    class Config:
        env_file = ".env"


settings = Settings()
