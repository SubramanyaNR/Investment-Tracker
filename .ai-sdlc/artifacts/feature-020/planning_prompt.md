# Planning Prompt

## Product Context
# Product Context - WealthSignal

WealthSignal is a personal multi-asset portfolio tracker for Indian retail investors. It provides unified portfolio observability (net worth, P&L, allocation) across crypto, mutual funds, and fixed income (FD/RD/PPF).

Key Principles:
- Portfolio observability is the primary goal.
- Not a trading or brokerage app.
- Focus on clarity and trust for the retail investor.


## Architecture Context
# Architecture Context

Stack:
- Backend: FastAPI (Python 3.11), SQLAlchemy 2.0 (async), Pydantic.
- Frontend: Next.js 16 (App Router), React 19, Tailwind 4.
- Database: Postgres 16 (UUID PKs, Numeric for money).
- Auth: Supabase Auth (PKCE flow).

Key Patterns:
- Same-origin /api proxy for backend access.
- All DB operations must be async.
- Identity derived only from verified JWT 'sub' claim.
- RLS enforced as a backstop; app-layer filtering is mandatory.


## Governance Context
# Governance Context

Operating Model:
- One system, seven lenses (PM, Investor Advisor, CTO, Architect, Eng Lead, QA, Security).
- Hard CEO approval gate at Step 6 of SDLC.
- Gated decisions: Architecture, Data Model, Auth, Security, Product Direction.
- Free lane: Docs, tests, copy polish within approved scope.


## Investor Experience Context
# Investor Experience Context

Investor Trust & Clarity:
- Metric comprehension: Are units and calculations clear?
- Dashboard clarity: Mobile-first status at a glance.
- Investor trust: Presentation must build confidence; limitations must be clear.
- Presentation of insights: Language must be investor-friendly, not overly technical.


## Request
# Feature: auth-toggle implementation

Implements the remediation plan approved in security workflow `secure-001`
(see `.ai-sdlc/artifacts/secure-001/remediation.md` and `validation.md` for
full threat model, acceptance criteria, and governance context). This
request is the execution of that already-approved security design — do not
re-litigate the design decisions here; flag anything that seems wrong
instead of silently deviating.

## Scope (R1–R5 from secure-001/remediation.md)

1. **R1 — `AUTH_ENABLED` bypass, single choke point.** In
   `backend/app/core/auth.py` (`get_current_user_id`) and/or
   `backend/app/api/deps.py` (`get_session`): when `AUTH_ENABLED=false`,
   skip JWT verification but resolve to the one existing bootstrapped
   admin `user_id` via a server-side DB lookup (`SELECT id FROM users
   LIMIT 1`) — never from client-supplied headers/params, never null/
   anonymous. If no user row exists yet, raise 500. No per-router
   conditionals. Default `AUTH_ENABLED=false`.

2. **R2 — `make reset-admin-password` + session invalidation.** New
   `backend/scripts/reset_admin_password.py`, CLI-only (never an HTTP
   route), interactive password prompt (no plaintext in argv/shell
   history), updates the existing single user row's `password_hash`
   (and optionally `email`) in place — no new row created. Add a
   `token_version` column (or equivalent) to `users`, checked against a
   JWT claim, incremented on reset so old tokens fail auth after a
   reset. New `Makefile` target `reset-admin-password`.

3. **R3 — read-only homescreen auth-status display.** No DB-backed
   mutable auth setting, no write/toggle API endpoint. Frontend reads
   current `AUTH_ENABLED` state (expose via a simple unauthenticated
   `GET /auth/status`-style read, or existing config surface) and
   displays it plus, when disabled, plain-language instructions to
   enable (env var + restart).

4. **R4 — danger banner, revised (amended post-planning, 2026-08-20).**
   The banner shows **whenever `AUTH_ENABLED=false`, full stop** —
   regardless of deployment context. This replaces the earlier design
   where `DEPLOYMENT_CONTEXT=local` (the default) would suppress the
   banner entirely, which planning review flagged as a double-negative
   gap: an operator who forgot to set *both* `AUTH_ENABLED=true` and
   `DEPLOYMENT_CONTEXT=hosted` correctly would get silently zero
   warning, on a project whose own history includes exactly that kind
   of drift (a dev-configured box that turned out to be the production
   VPS). Fail-safe wins over reduced nagging on localhost.

   `DEPLOYMENT_CONTEXT=local|hosted` is still captured (env var, no
   default — operator must set it explicitly at setup, no silent
   fallback), but now only affects banner **wording/severity**, not
   visibility: `hosted` gets the strongest copy ("anyone who can reach
   this address can view and edit your portfolio"), `local` gets a
   milder but still-present note. No request-origin/Host-header/
   client-IP heuristics anywhere, per the original reliability finding.

   Docs (`.env.example`, `docs/architecture/AUTH.md`,
   README/runbook) must state plainly: only enable auth if you actually
   need it (e.g., the instance is reachable by more than just you), and
   when you do, run `make reset-admin-password` first (ties R4 to R2 —
   enabling auth and rotating the default credentials are one
   recommended flow, not two independent steps).

5. **R5 — onboarding hardening.** `.env.example` `ADMIN_PASSWORD`
   placeholder must be obviously non-usable (e.g. `changeme`). README /
   `docs/runbooks/LOCAL-DEV.md` or `DEPLOY.md` gets a step: run `make
   reset-admin-password` before enabling auth or exposing the instance.

## Non-goals (explicitly out of scope, per secure-001)

- No multi-user / multi-tenancy support.
- No full session-store/revocation infra beyond the minimal
  `token_version` check.
- No changes to `bootstrap_admin_user()`'s first-boot-only semantics —
  it remains a permanent no-op after the first user row exists.
- No in-app write path for toggling `AUTH_ENABLED` — it is env +
  restart only.

## Acceptance criteria

Full checklist is `.ai-sdlc/artifacts/secure-001/validation.md`. QA stage
of this feature workflow should validate against that file directly
rather than re-deriving criteria.

## Docs to update

- `docs/architecture/AUTH.md` (or a superseding note to ADR 0005) to
  reflect the new model.
- `.env.example`
- README / relevant runbook for the `reset-admin-password` step.

