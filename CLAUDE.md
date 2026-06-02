# Investment Tracker

Personal multi-asset portfolio tracker (crypto, mutual funds, FD/RD/PPF/savings) for one Indian retail investor. FastAPI + Next.js + Postgres.

Deeper docs (read on demand, not auto-loaded): `docs/SCHEMA.md` (full columns), `docs/API.md` (full endpoints), `docs/ARCHITECTURE.md` (the WHY), `docs/VISION.md`, `docs/ROADMAP.md`.

## Stack
- **Backend** — FastAPI (Python 3.11), async SQLAlchemy 2.0 + asyncpg, Pydantic, HTTPX, APScheduler. Routers in `backend/app/api/`, business logic in `app/services/`, external API calls in `app/integrations/`, models in `app/db/models.py`.
- **Frontend** — Next.js 16 (App Router, all components `"use client"`), React 19, Tailwind 4, Recharts, Lucide. Every API call goes through `frontend/lib/api.ts`; response types live there too.
- **DB** — Postgres 16 (Docker, volume `postgres_data`). UUID PKs, `Numeric` for all money.
- **Migrations** — Alembic via `make migrate m="..."`.

> Note: this Next.js (16.x) has breaking changes vs older versions — see `frontend/AGENTS.md`; check `node_modules/next/dist/docs/` before writing Next code.

## Run — use `make`, never raw nohup/pkill
- `make dev` — postgres + backend (127.0.0.1:8000) + frontend prod build (:3000)
- `make restart` · `make stop` · `make build` · `make logs` · `make validate`
- `make migrate m="describe change"` — alembic autogenerate → upgrade → show current
- Logs: `/tmp/it-backend.log`, `/tmp/it-frontend.log`. Stop targets free the port (no pgrep self-match).

## How the app is accessed
Browser opens `http://172.23.80.6:3000` (the VM's IP). The frontend calls **same-origin `/api`**, which `frontend/next.config.ts` `rewrites()` proxies to `http://127.0.0.1:8000`. **Never** set `NEXT_PUBLIC_API_BASE_URL` to `localhost:8000` or a hardcoded IP — keep it `/api`. Symptom of breaking this: "Failed to load dashboard data" + empty crypto/MF search.

## Data model (full: docs/SCHEMA.md)
`assets` (UUID PK) + one 1:1 holding table per type: `crypto_holdings`, `mutual_fund_holdings`, `fixed_income_holdings`; plus `transactions`, `valuation_history`, `portfolio_snapshots`, `ai_insights`. `asset_type ∈ CRYPTO | MUTUAL_FUND | FD | RD | PPF | SAVINGS_ACC`. All asset-linked tables **CASCADE DELETE** from `assets`.

## Critical gotchas
- **POST /assets merges by `scheme_code` (MF) / `coingecko_id` (crypto)** — it averages into the existing holding and returns that asset; it does NOT create a separate one. Never reuse a real asset's scheme/coin for throwaway test data on the live DB — it mutates the real asset, and a later delete cascades real data away.
- **No DB backups exist** (`backup.sh` has never run). Destructive DB ops are irreversible — capture state first (`curl /assets`, `/transactions`).
- Don't test against the live single-user DB with real identifiers. Use unique names + unheld scheme/coin, or a scratch DB.
- MF valuation `invested = units × nav_at_purchase` (can differ slightly from rupees actually contributed).
- RD invested grows monthly (`principal × months_elapsed`); FD invests full principal day 1.
- MF NAV auto-fetched on fund select to avoid phantom day-1 P&L.
- AI insights: Gemini with a rule-based fallback; the Gemini call is wrapped so failures fall back instead of returning 500.

## Coding rules

### General
- Don't add features beyond what's asked. No "while I'm here" refactors.
- Comments only for non-obvious WHY, never to describe what code does.
- Don't create markdown docs unless asked. No backwards-compat shims — delete removed code fully.

### Backend
- All DB ops async (`await session.execute(...)`); asyncpg only, never sync drivers.
- New endpoints → existing router in `app/api/`; logic → `app/services/`; external calls → `app/integrations/`.
- `Numeric` (never `Float`) for financial values.
- New/changed column → `make migrate m="..."`. Never `create_all` for schema changes in prod.

### Frontend
- All components `"use client"`. API calls only via `frontend/lib/api.ts`.
- INR formatting: `₹` with Indian comma grouping (₹1,23,456).
- Theme: CSS custom props in `globals.css`, `[data-theme="dark"|"light"]` only.
- No emojis in UI unless requested. Response types defined in `lib/api.ts`.

### Database / infra
- UUID PKs, `Numeric` money, CASCADE DELETE from `assets`.
- Never delete or edit existing migration files — new change = new migration.
- Never commit `.env`, `.venv/`, `__pycache__/`, or `.pyc`. Secrets live in gitignored `.env`.

## Branch strategy
`master` = stable/deployable. Prefer a feature branch + PR; push to `master` only when the user explicitly asks.

## Env vars (secrets in `.env`, gitignored)
- `backend/.env`: `DATABASE_URL`, `COINGECKO_BASE_URL`, `MFAPI_BASE_URL`, `SCHEDULER_ENABLED`, `AI_PROVIDER` (`gemini`|`rules`), `GEMINI_API_KEY`, `GEMINI_MODEL`, `CORS_ORIGINS`.
- `frontend/.env.local`: `NEXT_PUBLIC_API_BASE_URL=/api` (baked at build — rebuild after changing).

## Known issues / tech debt
1. No auth — single-user, shared data (top priority).
2. No API caching — CoinGecko live on every request (rate-limit risk).
3. No tests — zero coverage; financial calcs must be tested before real money.
4. No "last updated" timestamp on prices.
5. `GET /transactions` unpaginated.

Schema is Alembic-managed (no `create_all`) — a fresh deploy must run `alembic upgrade head`.

## External services
CoinGecko (free, 30 req/min), MFAPI (free), Google Gemini (free tier). Full table + hosting/roadmap in `docs/VISION.md`.
