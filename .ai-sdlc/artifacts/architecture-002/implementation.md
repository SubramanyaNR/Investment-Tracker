# Implementation — Phase 1: Sandboxed Postgres + Migration Tooling

**Implemented by:** Claude (directly), not Gemini — the assigned `model_implementation` (Gemini)
hit a hard daily free-tier quota (20 req/day, `TerminalQuotaError`) after a transient-503 retry
storm on the first attempt burned through it. Founder decided to have Claude implement this phase
directly rather than wait for quota reset or enable billing. See `implementation.log` for the raw
Gemini failure output (two attempts, both quota/availability failures, zero files touched).

## What was built

- **`docker-compose.selfhost.yml`** (new, repo root) — a single `postgres:16` service, isolated
  from the existing `docker-compose.yml` (which remains the Supabase-era VPS-deploy file, untouched
  and still valid for the live app). Distinct container name, named volume, and database
  (`investment_tracker_selfhost`), so it cannot collide with anything else running on this host.
- No application code, auth code, or existing docker-compose.yml changes. No Supabase config,
  RLS, or `backend/.env` changes. No `VISION.md`/`ROADMAP.md` edits.

## Validation performed (not just code inspection)

1. `docker compose -f docker-compose.selfhost.yml up -d` — container started, healthcheck (`pg_isready`)
   passed.
2. `docker exec ... psql -c "SELECT version();"` — confirmed real Postgres 16.14 connectivity.
3. Ran the **existing, unmodified** Alembic migration chain (all 11 revisions, `10cf88b737b1` →
   `62c0aa1dd7cf`) against the sandbox via process-env overrides only
   (`DATABASE_URL`/`ADMIN_DATABASE_URL` pointed at the sandbox, `DB_SSL=` empty to disable TLS for
   this non-TLS local container) — **`backend/.env` was never modified**. All migrations applied
   cleanly with no errors.
4. `\dt` in the sandbox confirmed all 11 expected application tables exist
   (`assets`, `crypto_holdings`, `mutual_fund_holdings`, `fixed_income_holdings`,
   `manual_holdings`, `transactions`, `valuation_history`, `portfolio_snapshots`, `users`,
   `ai_insights`, `alembic_version`).
5. Confirmed the live app is unaffected: `make validate` still reports backend/frontend healthy,
   and `backend/.env`'s `DATABASE_URL` still points at Supabase (`git status` shows it untouched).

## Key finding

The existing schema and migration set have **no Supabase-specific dependency** — they applied
cleanly to vanilla Postgres 16, including the RLS-policy migrations (RLS itself works fine on any
Postgres; it's Supabase's *Auth* product, not its *Postgres*, that this pivot is actually replacing).
This de-risks Phase 2: the auth rewrite can be built and tested against this real, disposable
target without any Supabase dependency.

## Not done in this pass (explicitly out of scope, per planning.md)

- Auth code (bcrypt/JWT/cookies/refresh tokens) — Phase 2.
- Removing RLS policies — bundled with Phase 2 per the CEO decision log.
- Real data migration from Supabase — Phase 3, separately gated (backup + verified restore +
  rollback point required first).
- `VISION.md`/`ROADMAP.md` rewrite — later docs/release phase.
