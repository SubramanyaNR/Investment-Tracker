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

    supabase_jwks_url: str
    supabase_issuer: str
    supabase_jwt_audience: str = "authenticated"

    # DB TLS mode for asyncpg. Default "require" (Supabase). Set empty to disable
    # for a local non-TLS Postgres (e.g. the integration-test container).
    db_ssl: str | None = "require"

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

    # ── A9: JWKS unknown-kid negative cache ─────────────────────────────────
    jwks_negative_cache_ttl: int = 60        # seconds a confirmed-bad kid is remembered
    jwks_negative_cache_maxsize: int = 1000  # cap memory; evict oldest on overflow

    class Config:
        env_file = ".env"


settings = Settings()
