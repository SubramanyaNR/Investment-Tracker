# Architecture decisions (the WHY)

> Background rationale. The day-to-day gotchas live in CLAUDE.md "Critical gotchas".

### Stack choices
- **FastAPI (Python 3.11):** async-native, auto OpenAPI docs. SQLAlchemy 2.0 + asyncpg for non-blocking DB. APScheduler for cron-like jobs (daily snapshots, monthly SIP). Pydantic for validation/settings. HTTPX for async external calls.
- **Next.js 16 (TS, React 19):** App Router, `"use client"` throughout (client-rendered). Tailwind 4, Recharts, Lucide. All fetches via `frontend/lib/api.ts`.
- **Postgres 16:** reliability + JSON columns (allocation/metrics). Docker named volume `postgres_data`. asyncpg driver.
- **Alembic:** autogenerate detects model changes. `backend/migrate.sh` wraps autogenerate → upgrade → show current.

### Why no auth yet
Built single-user first to validate features fast. Auth changes every endpoint (~1-2 weeks); it's the next major milestone before launch.

### Why async everywhere
CoinGecko and MFAPI calls run concurrently during valuation recalculation. Async SQLAlchemy + asyncpg means DB calls don't block during API calls; APScheduler runs on the same loop.

### Why the valuation "upsert" pattern
`_upsert_valuation()` deletes today's record then inserts fresh — not a real upsert. Makes recalculating multiple times per day safe and idempotent. Slightly inefficient but correctness wins at this scale.

### Why CoinGecko free tier
With 60s response caching, 10,000 users make the same call frequency as 1. Free tier (30 calls/min) is never hit with caching. Paid tier only needed for sub-10s refresh.

### Why MFAPI (mfapi.in)
Free, no documented limits, covers all AMFI-registered Indian mutual funds (sourced from AMFI). `/search` enables fuzzy fund-name search.

### Why Google Gemini for AI insights
Generous free tier for a low-usage personal app. Model instructed to return structured JSON. Rule-based fallback ensures insights always work even if Gemini is unavailable or returns malformed JSON (the Gemini call is wrapped in try/except → falls back, never 500s).

### Why Docker for prod, direct for local dev
Docker prod = reproducible, easy VPS deploy. Local dev runs uvicorn + Next directly for hot reload and fast feedback; only Postgres runs in Docker locally (a data store needing no hot reload).

### Why no Kubernetes
Comfortably handles 100-10,000 users on one Hetzner CX21 with Docker Compose. K8s adds unjustified ops complexity at this scale. Revisit at 10,000+ users.

### Why monthly SIP auto-execution is in the scheduler
SIP is a core Indian MF behaviour. Scheduler runs 1st of month 09:00: fetches NAV, computes units, updates weighted-avg NAV, creates a BUY transaction — mirroring real SIPs.

### Why compound interest is server-side
FD/RD/PPF returns are deterministic given principal, rate, start date, frequency. No external API. Formula: A = P × (1 + r/n)^(n×t).

### RD special handling
For RD the invested amount grows monthly: invested = principal × months_elapsed. Unlike FD where full principal is invested on day 1.

### Why the MF phantom-P&L fix
If the user's purchase NAV differs from current live NAV, the initial valuation shows immediate (wrong) P&L. Fix: auto-fetch current NAV from MFAPI on fund select, pre-fill it, show the "as of" date; user can override with their real purchase NAV.

### Why the same-origin /api proxy
The app is opened from a browser at the VM's IP, not on the VM. A baked `NEXT_PUBLIC_API_BASE_URL` of `localhost:8000` resolves to the *browser's* machine; a hardcoded IP breaks when the IP changes. Instead the frontend calls same-origin `/api`, and `next.config.ts` `rewrites()` proxies `/api/*` → `http://127.0.0.1:8000/*` server-side. No CORS, no backend exposure, no IP in the build.
