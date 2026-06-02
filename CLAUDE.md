# Investment Tracker — Project Constitution
# The definitive reference for every AI agent, developer, or contributor working on this project.

---

## 1. WHAT IS THIS PROJECT AND WHY DOES IT EXIST

This is a **personal investment portfolio tracker** built for a single Indian retail investor who holds assets across multiple platforms and asset classes — cryptocurrency on exchanges, mutual funds on Groww/Kuvera, fixed deposits at banks, recurring deposits, PPF, and savings accounts.

**The problem it solves:** No single platform tracks all of these together. The investor had to manually reconcile across 4-5 apps and a spreadsheet to understand their true net worth, P&L, and allocation. This app unifies everything into one dashboard with live prices.

**The eventual goal:** Launch this as a paid SaaS product at ₹99/month for Indian retail investors who face the same multi-platform problem. The target market is ~8 crore active retail investors in India, of which a meaningful segment uses multiple platforms simultaneously.

---

## 2. CURRENT STATE (as of June 2026)

### What is DONE and working:
- Full asset management: add, view, delete assets across all types
- Crypto tracking: live prices via CoinGecko, P&L calculation
- Mutual fund tracking: live NAV via MFAPI, auto-SIP execution on 1st of month
- Fixed income tracking: compound interest calculator (FD, RD, PPF, Savings)
- Dashboard KPIs: total invested, current value, P&L, P&L %
- Net worth chart: line chart showing value vs invested over time
- Allocation charts: donut charts for asset type and liquidity split
- Transaction history: all buys, sells, deposits
- AI insights: Gemini 2.0 Flash analysis of portfolio (with rule-based fallback)
- Dark/light theme: persisted in localStorage
- Sell crypto: partial sell with transaction recording
- Redeem mutual fund: partial redemption with transaction recording
- Top-up savings/PPF: add to existing holding
- Auto-populate MF NAV: when selecting a fund, current NAV pre-fills from MFAPI
- Alembic database migrations: schema change management
- Docker Compose: full containerised stack (postgres + backend + frontend)
- Backup script: pg_dump with 7-backup rotation

### What is NOT yet built (planned):
- Auth + multi-tenancy (every user sees their own data — currently single-user only)
- User registration / login (Google OAuth via Auth.js)
- Pricing / payment integration (Razorpay)
- API response caching (CoinGecko rate limit protection)
- CI/CD pipeline (GitHub Actions auto-deploy)
- Staging environment
- Automated offsite backups (rclone to Google Drive)
- PWA support (manifest.json + service worker)
- Play Store publish via TWA
- Ansible playbook for server provisioning
- Calculation unit tests
- Monitoring / uptime alerting (UptimeRobot)
- Day-wise P&L charts
- "Last updated" timestamps on prices in the UI

---

## 3. TECH STACK AND WHY EACH PIECE WAS CHOSEN

### Backend: FastAPI (Python 3.11)
- Async-native, fast, automatic OpenAPI docs
- SQLAlchemy 2.0 with asyncpg for non-blocking DB access
- APScheduler for cron-like background jobs (daily snapshots, monthly SIP)
- Pydantic for validation and settings management
- HTTPX for async HTTP calls to external APIs

### Frontend: Next.js 16 (TypeScript, React 19)
- App Router, "use client" components throughout (all pages are client-side rendered)
- Tailwind CSS 4 for styling
- Recharts for charts (line chart, donut charts)
- Lucide React for icons
- All API calls are fetch-based from `frontend/lib/api.ts`

### Database: PostgreSQL 16
- Chosen for reliability, JSON column support (allocation, metrics stored as JSON)
- Runs in Docker container with named volume (data persists across restarts)
- asyncpg driver for async access

### Migrations: Alembic
- Autogenerate detects model changes, creates migration files
- `backend/migrate.sh` is the convenience wrapper: autogenerate → upgrade → show current
- Usage: `./migrate.sh "describe what changed"`

### Infrastructure: Docker Compose
- All three services (postgres, backend, frontend) defined in `docker-compose.yml`
- Named volume `postgres_data` persists all database data
- Health check on postgres: backend waits for it before starting
- Port 5432 exposed to host (required for running backend directly during local dev)
- CORS_ORIGINS and NEXT_PUBLIC_API_BASE_URL are env-var driven for deployment flexibility

---

## 4. ARCHITECTURE DECISIONS (the WHY behind key choices)

### Why no auth yet
The app was built as single-user first to validate the feature set quickly. Auth adds 1-2 weeks of work and changes every endpoint. It will be added as the next major milestone before public launch.

### Why async everywhere
CoinGecko and MFAPI calls happen concurrently during valuation recalculation. Async SQLAlchemy + asyncpg means DB calls don't block during API calls. APScheduler runs on the same async loop.

### Why valuation upsert pattern
`_upsert_valuation()` deletes today's record then inserts fresh — not a real upsert. This means recalculating multiple times per day is safe and idempotent. The downside is slightly inefficient but correctness matters more at this scale.

### Why CoinGecko free tier
With API response caching (60 seconds), even 10,000 users make the same call frequency as 1 user. The free tier limit of 30 calls/minute is never hit with caching. Paid tier is not needed until real-time prices (sub-10 second refresh) are required.

### Why MFAPI (mfapi.in)
Free, no rate limits documented, covers all AMFI-registered mutual funds in India. NAV data is sourced from AMFI directly. The `/search` endpoint enables fuzzy fund name search.

### Why Google Gemini for AI insights
Free tier is generous for low-usage personal app. The model is instructed to return structured JSON observations. Rule-based fallback ensures insights always work even if Gemini is unavailable or returns malformed JSON.

### Why Docker for production, direct for local dev
Docker for production: reproducible environment, easy VPS deployment, no manual dependency management.
Direct (uvicorn + npm run dev) for local dev: hot reload works, faster feedback loop, no container rebuild on every change.
Only Postgres runs in Docker locally — it's a data store with no need for hot reload.

### Why no Kubernetes
This app will comfortably handle 100-10,000 users on a single Hetzner CX21 ($5/month VPS) with Docker Compose. Kubernetes adds operational complexity that is not justified at this scale. Revisit at 10,000+ users.

### Why monthly SIP auto-execution is in the scheduler
SIP (Systematic Investment Plan) is a core Indian mutual fund behaviour — users invest a fixed amount monthly. The scheduler runs on the 1st of each month at 09:00, fetches current NAV, calculates units, updates weighted average NAV, and creates a BUY transaction. This mirrors how real SIPs work.

### Why compound interest is calculated server-side
Fixed income returns (FD, RD, PPF) are deterministic — given principal, rate, start date, and compounding frequency, the current value is always calculable. No external API needed. The formula is A = P × (1 + r/n)^(n×t).

### RD (Recurring Deposit) special handling
For RD, the "invested amount" grows every month (new deposit). The formula for invested = principal × months_elapsed. This is different from FD where the full principal is invested on day 1.

### Why the MF phantom P&L bug was fixed
When a mutual fund is added, the user enters NAV at purchase. If this NAV differs from the current live NAV on MFAPI, the initial valuation shows a P&L immediately — which is wrong. Fix: auto-fetch current NAV from MFAPI when the user selects a fund, pre-fill it, and show the "as of" date. User can override with their actual purchase NAV. This prevents the phantom loss bug.

---

## 5. DATABASE SCHEMA (complete)

```
assets                          — master record for every investment
  id (UUID PK)
  name (String)                 — user-defined label
  asset_type (String)           — CRYPTO | MUTUAL_FUND | FD | RD | PPF | SAVINGS_ACC
  category (String)             — crypto | equity | debt | savings
  liquidity_tier (String)       — LIQUID | LOCKED
  created_at (DateTime TZ)

crypto_holdings                 — 1:1 with assets (asset_type=CRYPTO)
  asset_id (UUID PK FK→assets)
  coingecko_id (String)         — e.g. "bitcoin", "ethereum"
  symbol (String)               — e.g. "BTC"
  quantity (Numeric 24,10)
  avg_buy_price (Numeric 18,6)  — INR, weighted average across buys

mutual_fund_holdings            — 1:1 with assets (asset_type=MUTUAL_FUND)
  asset_id (UUID PK FK→assets)
  scheme_code (String)          — MFAPI scheme code
  units (Numeric 24,10)         — calculated: amount_invested / nav_at_purchase
  nav_at_purchase (Numeric 18,6)— weighted average NAV
  monthly_sip (Numeric 18,2)    — nullable; if set, auto-invested on 1st of month

fixed_income_holdings           — 1:1 with assets (FD|RD|PPF|SAVINGS_ACC)
  asset_id (UUID PK FK→assets)
  principal (Numeric 18,2)      — for RD: monthly instalment amount
  annual_rate (Numeric 8,4)     — percentage e.g. 7.1
  start_date (Date)
  maturity_date (Date nullable)
  compounding_frequency (String) — MONTHLY | QUARTERLY | YEARLY

transactions                    — every financial event
  id (UUID PK)
  asset_id (UUID FK→assets CASCADE)
  transaction_type (String)     — BUY | SELL | DEPOSIT
  transaction_date (Date)
  amount (Numeric 18,2)
  units (Numeric 24,8 nullable)
  price_per_unit (Numeric 18,6 nullable)

valuation_history               — daily snapshot per asset
  id (UUID PK)
  asset_id (UUID FK→assets CASCADE)
  valuation_date (Date)
  invested_amount (Numeric 18,2)
  current_value (Numeric 18,2)
  pnl (Numeric 18,2)
  source (String)               — coingecko | mfapi | compound_interest | initial

portfolio_snapshots             — daily portfolio-level rollup (UNIQUE per date)
  id (UUID PK)
  snapshot_date (Date UNIQUE)
  total_invested (Numeric 18,2)
  total_value (Numeric 18,2)
  total_pnl (Numeric 18,2)
  allocation (JSON)
  liquidity (JSON)
  metrics (JSON)

ai_insights                     — stored AI analysis results
  id (UUID PK)
  insight_date (Date)
  observations (JSON)           — [{category, severity, title, message}]
  model (String)                — "gemini" | "rules"
```

All FK relationships have CASCADE DELETE — deleting an asset cleans up all related records.

---

## 6. API ENDPOINTS (complete reference)

```
GET  /health                                      → {status: "ok"}

GET  /dashboard                                   → {total_invested, total_value, total_pnl, pnl_percent}

GET  /assets                                      → Asset[] with nested holdings
POST /assets                                      → create asset (polymorphic by asset_type)
DELETE /assets/{asset_id}                         → delete asset + all related data

POST /assets/{asset_id}/sell-crypto               → {quantity} → reduce crypto holding
POST /assets/{asset_id}/redeem-mf                 → {units} → reduce MF holding
POST /assets/{asset_id}/top-up                    → {amount} → add to savings/PPF principal

GET  /valuations/latest                           → latest Valuation per asset
POST /valuations/recalculate                      → refresh all prices, update valuations + snapshot

GET  /snapshots                                   → Snapshot[] ordered by date

GET  /transactions                                → TxRecord[] ordered by date desc

GET  /market/crypto/top                           → top 10 CoinGecko coins (INR)
GET  /market/mutual-funds/search?q={query}        → MutualFundScheme[] (min 3 chars, max 20)
GET  /market/mutual-funds/{scheme_code}/nav       → {scheme_code, nav, date}

POST /insights/refresh                            → generate + store AI insights
GET  /insights/latest                             → most recent ai_insights record
```

---

## 7. ENVIRONMENT VARIABLES

### Backend (`backend/.env`)
```
DATABASE_URL=postgresql+asyncpg://investment_user:investment_pass@localhost:5432/investment_db
COINGECKO_BASE_URL=https://api.coingecko.com/api/v3
MFAPI_BASE_URL=https://api.mfapi.in/mf
SCHEDULER_ENABLED=true
AI_PROVIDER=gemini                    # or "rules" for no Gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
CORS_ORIGINS=http://localhost:3000    # comma-separated for multiple
```

### Root `.env` (docker-compose variable substitution)
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000   # browser-visible backend URL
CORS_ORIGINS=http://localhost:3000               # must match frontend origin
```

When deploying to a VPS, replace `localhost` with the server's IP or domain.

---

## 8. LOCAL DEVELOPMENT SETUP

```bash
# Start only Postgres in Docker
docker compose up postgres -d

# Backend (in backend/ directory)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (in frontend/ directory)
npm install
npm run dev

# App runs at http://localhost:3000
# API runs at http://localhost:8000
```

For production (VPS), all three services run in Docker:
```bash
docker compose up --build -d
```

---

## 9. SCHEMA CHANGE WORKFLOW

When you add or modify a column in `backend/app/db/models.py`:
```bash
cd backend
source .venv/bin/activate
./migrate.sh "describe what you changed"
```

This: autogenerates a migration file → applies it → shows current state.
Never manually write SQL migrations. Always use Alembic autogenerate.

---

## 10. PRODUCT VISION AND ROADMAP

### Vision
A beautifully simple, privacy-respecting investment tracker for Indian retail investors who hold assets across multiple platforms. Not another broker app. Not another fintech with an agenda. Just honest, unified tracking.

### Pricing model
- 21-day free trial (no credit card required)
- ₹99/month or ₹999/year
- Early bird pricing for first 100 users (locks in forever)
- Single plan, no free tier complexity at launch

### Target user
Indian retail investor, 25-40 years old, holds crypto + mutual funds + at least one fixed income instrument, frustrated by switching between 4-5 apps, willing to pay ₹99 for a unified view.

### Hosting plan
- Hetzner CX21 VPS (~$5/month) for up to ~10,000 users
- Docker Compose (no Kubernetes needed at this scale)
- Domain + Nginx + Certbot (HTTPS)
- Backup container + rclone to Google Drive
- UptimeRobot for monitoring

### Distribution strategy (0 → 100 users)
- r/IndiaInvestments, r/IndianStockMarket (organic posts)
- Finance Twitter/X — build in public
- Product Hunt launch
- Telegram finance channels (sponsored posts ₹500-2000/channel)
- No paid ads until conversion is proven

### Scale reference
- 100 users → ₹9,900/month revenue, ~₹690/month costs → net ~₹9,200/month
- 1000 users → ~₹99,000/month revenue, same $9 server cost
- CoinGecko free tier sufficient at any user count with 60-second caching

---

## 11. NEXT MAJOR MILESTONES (in order)

### Milestone 1: Auth + Multi-tenancy (CURRENT PRIORITY)
- Add `users` table to DB
- Add `user_id` FK to `assets` table (every asset belongs to a user)
- All API endpoints filter by authenticated user
- Google OAuth login via Auth.js (NextAuth v5)
- Sessions stored in own Postgres DB
- Protect all routes behind auth middleware
- This is the only blocker before public launch

### Milestone 2: API Caching
- Cache CoinGecko responses for 60 seconds (in-memory or Redis)
- Cache MFAPI NAV responses for 5 minutes
- Without this, 100 simultaneous refreshes can hit rate limits

### Milestone 3: Production Infrastructure
- Hetzner VPS
- Domain + Certbot SSL
- GitHub Actions CI/CD (push to master → auto-deploy)
- Backup container + rclone to Google Drive
- UptimeRobot monitoring

### Milestone 4: PWA + Play Store
- manifest.json + service worker (installable on phone)
- TWA wrapper (Bubblewrap) for Google Play Store submission
- HTTPS is a prerequisite (Milestone 3 must be complete)

### Milestone 5: Payments
- Razorpay integration (supports UPI, cards, netbanking)
- Gate features behind subscription check
- Webhook for payment confirmation

### Milestone 6: Test suite
- Unit tests for all calculation logic (P&L, compound interest, MF returns)
- API integration tests with test database
- Smoke test script that runs after every deploy

---

## 12. CODING RULES FOR THIS PROJECT

### General
- Do not add features beyond what is asked. No "while I'm here" refactors.
- Do not add comments explaining what the code does. Only add comments for non-obvious WHY.
- Do not create markdown documentation files unless explicitly asked.
- No backwards-compatibility shims. If something is removed, delete it completely.

### Backend
- All DB operations must be async (use `await session.execute(...)`, never sync SQLAlchemy)
- Use `asyncpg` — never switch to psycopg2 or sync drivers
- New endpoints go in the appropriate existing router file in `app/api/`
- New business logic goes in `app/services/`, not in router files
- New external API calls go in `app/integrations/`
- Always use `Numeric` (not `Float`) for financial values to avoid floating point errors
- When adding a new column to a model, run `./migrate.sh "description"` — never use `create_all` for schema changes in production

### Frontend
- All components are `"use client"` — this is a client-rendered app
- API calls go through `frontend/lib/api.ts` — never call fetch directly in components
- INR formatting: use `₹` symbol with comma-separated Indian numbering (e.g. ₹1,23,456)
- Theme: CSS custom properties in `globals.css`, `[data-theme="dark"]` and `[data-theme="light"]` only — retro theme was removed
- No emojis in UI unless explicitly requested
- Types for all API responses are defined in `frontend/lib/api.ts`

### Database
- UUID primary keys on all tables
- `Numeric` types for all monetary values (never Float)
- All asset-related tables have `CASCADE DELETE` from `assets`
- Never delete migration files. Never edit existing migration files.
- New schema changes = new migration file via `./migrate.sh`

### Infrastructure
- Never commit `.env` files
- Never commit `.venv/` (already in .gitignore — was cleaned up from git history)
- Never commit `__pycache__/` or `.pyc` files
- All secrets go in `.env` files, which are gitignored
- Docker Compose is for production. Local dev runs backend and frontend directly.

---

## 13. BRANCH STRATEGY

- `master` — stable, deployable code
- `claude/practical-newton-DJjvS` — current active development branch
- All Claude Code work goes to the designated branch, never directly to master

---

## 14. KNOWN ISSUES AND TECH DEBT

1. **No auth** — single-user app, all data shared. Top priority to fix.
2. **No API caching** — CoinGecko calls are live on every request. Risk of rate limiting with multiple users.
3. **init_db() uses create_all** — startup creates tables if missing. Should be removed in favour of Alembic-only schema management before production.
4. **No tests** — zero test coverage. Financial calculations must be tested before taking real user money.
5. **CORS hardcoded fallback** — default is `http://localhost:3000`. Must be set correctly for production.
6. **No "last updated" timestamp on prices** — user can't tell if prices are stale.
7. **No error boundaries in frontend** — unhandled API errors can crash the UI silently.
8. **Transactions list capped at implicit limit** — `GET /transactions` returns all records. Should be paginated before scale.

---

## 15. EXTERNAL SERVICES REFERENCE

| Service | Purpose | Tier | Limit |
|---|---|---|---|
| CoinGecko API | Crypto prices, top coins | Free (Demo) | 30 req/min |
| MFAPI (mfapi.in) | MF NAV, scheme search | Free | No documented limit |
| Google Gemini | AI portfolio insights | Free tier | Generous for low usage |
| Razorpay | Payments (not yet integrated) | Pay per transaction | 2% per transaction |
| Hetzner CX21 | VPS hosting (planned) | $5/month | 2 vCPU, 4GB RAM, 20TB traffic |
| Cloudflare Registrar | Domain (planned) | ~$10/year | - |
| Google Drive + rclone | Offsite backups (planned) | Free 15GB | - |
| UptimeRobot | Uptime monitoring (planned) | Free | 50 monitors |
