# Implementation Prompt

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


## Planning
## Review: auth-toggle implementation (secure-001 execution)

**Top concern — verify the approval gate actually closed.** CLAUDE.md is explicit that authentication and security-model changes require CEO approval before implementation begins, and that Claude "must stop at approval gates." Project memory shows an "Auth disable discussion" opened 2026-08-18 with **no decision**, meant to resume 2026-08-19. Today is 2026-08-20, and this request asserts secure-001's remediation is "already approved" and treats re-litigating it as out of scope. The `.ai-sdlc/artifacts/secure-001/` directory does exist (per git status), which is a good sign the workflow progressed, but given how recently this was an open, undecided discussion, I'd confirm `remediation.md`/`validation.md` actually carry a recorded CEO approval (not just a completed planning stage) before treating R1–R5 as greenlit. This is the one place where "flag instead of silently deviate" clearly applies.

**R4 — undefined behavior when `DEPLOYMENT_CONTEXT` is unset.** The spec says "no default — operator must set it explicitly," but doesn't say what happens if they don't. This is exactly the failure mode the R4 revision was written to close (silent under-warning from a missing/incorrect setting, echoing the earlier dev-box-that-was-actually-prod incident). Recommend making this explicit in the plan: either the app refuses to start / fails loudly with `AUTH_ENABLED=false` and `DEPLOYMENT_CONTEXT` unset, or the banner defaults to the strongest ("hosted") copy when the var is missing. Leaving it implicit invites an implementer to quietly fall back to the milder "local" copy, reproducing the double-negative gap under a new name.

**R3 — status endpoint payload underspecified for R4's needs.** R4's frontend banner needs both `AUTH_ENABLED` and `DEPLOYMENT_CONTEXT` to pick wording/severity, but R3 only says the endpoint exposes "current AUTH_ENABLED state." Worth making explicit that `GET /auth/status` (or equivalent) returns both fields — otherwise the frontend has no sanctioned way to get `DEPLOYMENT_CONTEXT` and someone will improvise a second surface.

**R1 — single-row invariant isn't enforced, only assumed.** `SELECT id FROM users LIMIT 1` combined with "`bootstrap_admin_user()` is a permanent no-op after the first row exists" is coherent as long as no other path can ever insert a second user row. That invariant is presently just convention, not a DB constraint. Not asking for a schema change (that would itself need approval), but worth a one-line acceptance check confirming there's genuinely no code path that inserts additional users, so `LIMIT 1` can't silently pick the wrong row later.

**R1 — startup ordering.** If `AUTH_ENABLED=false` and no user row exists yet, every request 500s per spec. Fine as designed, but confirm `bootstrap_admin_user()` runs synchronously in the app startup lifecycle before the server accepts traffic, so this 500 window is theoretical rather than a real first-boot outage.

**R2 — reset-admin-password / AUTH_ENABLED interaction worth a doc line.** Rotating `token_version` only matters once a JWT is actually being checked, i.e., when `AUTH_ENABLED=true`. Docs should say plainly that running `reset-admin-password` while auth is disabled is a no-op from a security standpoint (there's no session to invalidate), so operators don't get false confidence from running it alone.

**Minor / non-blocking:**
- Per-request DB lookup for the bypass user is fine at single-user scale; not worth optimizing.
- `/auth/status` being unauthenticated is correct (needed pre-login) and doesn't add meaningful disclosure beyond what the banner already reveals.

Everything else — the single-choke-point design, CLI-only password reset, no DB-backed toggle, `changeme` placeholder hardening — is consistent with the stated non-goals and matches the architecture's existing patterns (JWT-only identity, app-layer enforcement). No pushback on the core design, just the approval-gate check and the two spec gaps (`DEPLOYMENT_CONTEXT` fallback, `/auth/status` payload) above.
