# WealthSignal (Investment Tracker)

Personal multi-asset portfolio tracker (crypto, mutual funds, FD/RD/PPF/savings) for Indian retail
investors. **Portfolio observability** — net worth, P&L, allocation unified across platforms.
**Not** a trading / brokerage / expense / budgeting / banking app. FastAPI + Next.js + Postgres.

## Doc routing — load only what the task needs
`CLAUDE.md` is the always-loaded layer; everything else is on-demand. Pick from `docs/INDEX.md`:
- New feature / any change → `docs/operating-model/SDLC.md` (run `/feature` first)
- What needs CEO approval → `docs/operating-model/GOVERNANCE.md`; review lenses → `ROLES.md`
- The WHY + decisions → `docs/architecture/OVERVIEW.md`, `architecture/decisions/`
- Schema → `architecture/DATA-MODEL.md` · API → `architecture/API.md` · auth → `architecture/AUTH.md`
- Product → `product/VISION.md`, `product/PRINCIPLES.md`, `product/ROADMAP.md`
- A shipped feature's behaviour → `features/<feature>.md`
- Deploy / backup / incident / local dev / security → `runbooks/*`

## How we work (operating model)
One system reasons through seven lenses (PM, Investor Advisor, CTO, Architect, Eng Lead, QA,
Security) and **stops at the CEO approval gate**. For any non-trivial change run **`/feature`**: it
produces Product → Architecture → Security → Engineering → QA reviews, then **STOPS** — implement
only after the CEO says "approved".

**Gated (approval required before Edit/Write/migrate):** architecture, data model/migrations, auth,
security, product direction, infra, prod deploy. A `PreToolUse` hook enforces this on gated code
paths. **Free lane (no gate):** docs, tests, copy polish within approved scope. Full rules:
`docs/operating-model/GOVERNANCE.md`. Default to monolith-first; no microservices/K8s/CQRS/event-
sourcing without written CTO+Architect sign-off.

## Stack
- **Backend** — FastAPI (Python 3.11), async SQLAlchemy 2.0 + asyncpg, Pydantic, HTTPX, APScheduler. Routers in `backend/app/api/`, business logic in `app/services/`, external API calls in `app/integrations/`, models in `app/db/models.py`. Auth in `app/core/auth.py`.
- **Frontend** — Next.js 16 (App Router, all components `"use client"`), React 19, Tailwind 4, Recharts, Lucide. Every API call goes through `frontend/lib/api.ts`; response types live there too.
- **DB** — Postgres 16. UUID PKs, `Numeric` for all money. Request path connects as least-privileged `app_user` (RLS); migrations/scheduler use the admin DSN.
- **Migrations** — Alembic via `make migrate m="..."`.

> Note: this Next.js (16.x) has breaking changes vs older versions — see `frontend/AGENTS.md`; check `node_modules/next/dist/docs/` before writing Next code.

## Run — use `make`, never raw nohup/pkill
- `make dev` — postgres + backend (127.0.0.1:8000) + frontend prod build (:3000)
- `make restart` · `make stop` · `make build` · `make logs` · `make validate`
- `make migrate m="describe change"` — alembic autogenerate → upgrade → show current (gated)
- Logs: `/tmp/it-backend.log`, `/tmp/it-frontend.log`. Validate against a **prod build**, not `npm run dev`. Full table: `docs/runbooks/LOCAL-DEV.md`.

## How the app is accessed
Browser opens `http://172.23.80.6:3000` (the VM's IP). The frontend calls **same-origin `/api`**, which `frontend/next.config.ts` `rewrites()` proxies to `http://127.0.0.1:8000`. **Never** set `NEXT_PUBLIC_API_BASE_URL` to `localhost:8000` or a hardcoded IP — keep it `/api`. Symptom of breaking this: "Failed to load dashboard data" + empty crypto/MF search.

## Data model (full: `docs/architecture/DATA-MODEL.md`)
`assets` (UUID PK) + one 1:1 holding table per type: `crypto_holdings`, `mutual_fund_holdings`, `fixed_income_holdings`; plus `transactions`, `valuation_history`, `portfolio_snapshots`, `ai_insights`. `asset_type ∈ CRYPTO | MUTUAL_FUND | FD | RD | PPF | SAVINGS_ACC`. All asset-linked tables **CASCADE DELETE** from `assets`. Every user-owned row has `user_id` (NOT NULL); every query filters by the JWT `sub` (`docs/architecture/AUTH.md`).

## Critical gotchas
- **POST /assets merges by `scheme_code` (MF) / `coingecko_id` (crypto)** — it averages into the existing holding and returns that asset; it does NOT create a separate one. Never reuse a real asset's scheme/coin for throwaway test data on the live DB — it mutates the real asset, and a later delete cascades real data away. (Scoped per user.)
- **No DB backups run automatically** (`make backup` is manual). Destructive DB ops are irreversible — capture state first; load the `safe-db-op` skill.
- Don't test against the live DB with real identifiers. Use unique names + unheld scheme/coin, or a scratch DB.
- MF valuation `invested = units × nav_at_purchase` (can differ slightly from rupees actually contributed).
- RD invested grows monthly (`principal × months_elapsed`); FD invests full principal day 1.
- MF NAV auto-fetched on fund select to avoid phantom day-1 P&L.
- AI insights: Gemini with a rule-based fallback; the Gemini call is wrapped so failures fall back instead of returning 500.
- **Never trust a client-supplied `user_id`** — identity comes only from the verified JWT `sub`; ownership checks return 404 (not 403) for another user's row.

## Coding rules

### General
- Don't add features beyond what's asked. No "while I'm here" refactors.
- Comments only for non-obvious WHY, never to describe what code does.
- Don't create markdown docs unless asked. No backwards-compat shims — delete removed code fully.

### Backend
- All DB ops async (`await session.execute(...)`); asyncpg only, never sync drivers.
- New endpoints → existing router in `app/api/`; logic → `app/services/`; external calls → `app/integrations/`.
- `Numeric` (never `Float`) for financial values.
- Every query on a user-owned table filters by `user_id` (RLS is a backstop, not a license to skip it).
- New/changed column → `make migrate m="..."`. Never `create_all` for schema changes in prod.

### Frontend
- All components `"use client"`. API calls only via `frontend/lib/api.ts`.
- INR formatting: `₹` with Indian comma grouping (₹1,23,456).
- Theme: CSS custom props in `globals.css`, `[data-theme="dark"|"light"]` only.
- No emojis in UI unless requested. Response types defined in `lib/api.ts`.

### Database / infra
- UUID PKs, `Numeric` money, CASCADE DELETE from `assets`.
- Never delete or edit existing migration files — new change = new migration.
- Never commit `.env`, `.venv/`, `__pycache__/`, `.pyc`, or `.claude/state/`. Secrets live in gitignored `.env` (list: `docs/runbooks/LOCAL-DEV.md`).

## Branch strategy
`master` = stable/deployable. Prefer a feature branch + PR; push to `master` only when the CEO explicitly asks.

## Known issues / tech debt
1. Auth + multi-tenancy done; M2 fully resolved (A5, A9); M4 (token revocation) accepted Free-plan limitation — revisit on Pro. See `docs/runbooks/SECURITY-AUDIT.md`.
2. No tests — zero coverage; financial calcs must be tested before real money.
3. No "last updated" timestamp on prices (deferred to post-VPS).

Schema is Alembic-managed (no `create_all`) — a fresh deploy must run `alembic upgrade head`, and `app_user` must be provisioned once (`docs/runbooks/DEPLOY.md`).

## External services
CoinGecko (free, 30 req/min), MFAPI (free), Google Gemini (free tier), Supabase Auth. Full table + hosting/roadmap in `docs/product/VISION.md`.

----

## Engineering Behaviour

Before implementation:

* State important assumptions.
* Surface ambiguity rather than guessing.
* Present simpler alternatives when appropriate.
* Push back on unnecessary complexity.
* Ask for clarification when requirements are unclear.

When multiple valid approaches exist:

* Present the recommended option.
* Explain tradeoffs briefly.
* Await CEO approval on gated decisions.

Prefer clear reasoning over immediate implementation.

## Change Discipline

Make the smallest change that solves the approved problem.

* Do not modify adjacent systems unless required.
* Do not introduce abstractions without a demonstrated need.
* Match existing code style and architecture.
* Every changed file should directly support the approved objective.

If unrelated issues are discovered:

* Record them.
* Report them.
* Do not fix them without approval.

## Validation Requirements

Implementation is not complete until validated.

Every completed roadmap item should include:

* What changed
* What was tested
* Validation results
* Remaining risks

Do not declare success based solely on code review.

Prefer:

1. Automated tests
2. Integration validation
3. Production-build verification

when applicable.

## Continuous Improvement Policy

Claude may continuously improve:

* Documentation
* Engineering standards
* Test coverage
* Validation procedures
* Runbooks
* Technical debt tracking
* Lessons learned
* ADR quality
* Roadmap progress tracking

Claude may not autonomously change:

* Product direction
* Product requirements
* Architecture
* Authentication model
* Security model
* Database design
* Infrastructure strategy
* Hosting decisions
* Roadmap priorities

without explicit CEO approval.

After every completed roadmap item:

1. Record lessons learned.
2. Update technical debt register.
3. Update relevant documentation.
4. Suggest process improvements.
5. Report discovered risks and tradeoffs.
6. Stop and await CEO approval before proceeding.

Continuous improvement should focus on:

* Reliability
* Maintainability
* Observability
* Security
* Testability

without altering approved product direction.
