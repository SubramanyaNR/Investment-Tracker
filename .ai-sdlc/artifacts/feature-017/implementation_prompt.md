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
# Review — Full Cutover: Custom Auth Rewrite + Fresh Local Postgres

## Overall verdict
Scope is coherent and well-justified given the corrected facts (Supabase still live, auth rewrite not actually started). Dropping data migration genuinely removes the highest-risk part of the original plan. The design carries forward already-approved decisions rather than re-litigating them, which is the right move under the SDLC rules. A few gaps should be closed before implementation starts, and one process question in the request should be answered explicitly rather than left open.

## Governance
The four gated categories (architecture, DB schema, migrations, auth/security) are all touched, and the request states founder approval was given directly in-session. That satisfies the CEO gate as described — but the plan should still stop for explicit confirmation of the *auth design specifics* below before code is written, since some of them weren't nailed down in the original `architecture-002` record and are being decided implicitly by omission here.

## Security (highest-risk lens for this request)
- **CSRF pattern unspecified.** "SameSite + CSRF token" needs to be concrete: is this double-submit cookie (readable CSRF cookie compared to a header) or a synchronizer token tied to server session state? These have different implementation and threat-model implications. Pick one explicitly before implementation.
- **Refresh token storage not detailed.** For "revocable" to mean anything, the table needs at minimum: hashed token value (never store raw), expiry, revoked flag, and ideally issued-at/last-used for audit. Worth stating this explicitly in the migration plan rather than leaving it implicit.
- **Bootstrap idempotency.** `ADMIN_EMAIL`/`ADMIN_PASSWORD` staying in `.env` after first run is a footgun — if bootstrap re-runs on every restart (container recreate, crash loop), does it reset the admin password back to the env value every time? Needs an explicit "already bootstrapped" guard (e.g., check `users` table non-empty) before write.
- **No brute-force protection mentioned.** Single-user system, but it's now the *only* front door (no email reset). A basic rate limit or lockout on login is cheap insurance against being locked out by an attacker guessing, or against your own automation hammering the endpoint.
- **Lockout recovery path.** No email reset by design — fine — but there's no stated fallback if the bootstrap or login path has a bug post-cutover. Recommend documenting (in the runbook, not code) a manual SQL path to reset `password_hash` directly, so a bug doesn't strand the only account.
- **Cookie domain/scope risk, specific to this deployment.** Per prior session state, the frontend is reached via VM IP through a same-origin `/api` proxy, and the box's real IP recently changed (172.23.80.6 → <vps-ip> per earlier confirmation). This is the *first* time cookie-based session storage is being introduced (Supabase's client SDK previously owned token storage). Cookie `Domain`/`Secure`/`SameSite` settings need to be verified against however the app is actually being accessed today, not assumed from local dev — this is a plausible silent-failure point (login succeeds, cookie never gets sent back) that's easy to miss until manual testing.

## Architecture / Technical
- Two-container split (disposable sandbox vs. real target) is the right call and matches earlier planning — good that it's carried forward rather than collapsed for convenience.
- "Full cutover" should explicitly include removing the Supabase client SDK dependency (frontend `@supabase/*` package, backend if any) and any other Supabase touchpoints beyond login (session refresh listeners, auth context). Worth a quick audit pass before declaring done — otherwise this becomes a partial cutover with dead code and a false sense of completion.
- JWT secret generation method isn't specified (should be high-entropy, generated once, never committed) — trivial but worth stating so it's not left to implementation-time improvisation.

## Sequencing question (explicitly raised in the request)
The request asks whether the earlier "split into checkpointed sub-stages" recommendation still applies now that data migration is out of scope. Recommendation: a single implementation pass is reasonable for the *code* (auth rewrite + migration can be written and reviewed together), but keep the **smoke-test step in section 4 as a hard gate**, not a formality — if login/dashboard/asset-add fails after repointing, the plan should fall back to leaving the backend on the old Supabase/JWKS config rather than being left in a half-cut-over, down state. That's less "two sub-stages" and more "don't let code-complete and switch-flipped happen atomically without a verified checkpoint in between," which section 4 already implies — just make it explicit as a rollback trigger.

## QA
Listed test coverage (login, expiry/refresh, revocation, bootstrap, ownership) is the right required set per ROADMAP step 5. Add two:
- A negative test proving an old Supabase-issued JWT is rejected post-cutover (proves the old path is actually gone, not just additive).
- A CSRF test (mutating request without/with wrong token is rejected).

## Product / Investor Experience
No end-user–facing change (single-user system), so low product risk. The one thing worth naming explicitly rather than leaving implicit: this cutover requires planned downtime (stop backend → repoint → bootstrap → restart). Fine for a single-user app, but call it out as "planned downtime" in the execution plan rather than something implied only by reading the sequence.

## Summary of open items to resolve before implementation
1. Pick concrete CSRF mechanism.
2. Specify refresh-token table fields (hashed value, expiry, revoked flag).
3. Add bootstrap idempotency guard.
4. Add basic login rate-limiting/lockout.
5. Document a manual recovery path for a locked-out admin account.
6. Verify cookie domain/Secure/SameSite settings against actual current access path (VM IP + `/api` proxy), given the recent IP change.
7. Scope "full cutover" to include removing Supabase SDK/client code, not just the JWKS verification path.
8. Treat the post-repoint smoke test as a hard rollback gate, not just a checklist item.
