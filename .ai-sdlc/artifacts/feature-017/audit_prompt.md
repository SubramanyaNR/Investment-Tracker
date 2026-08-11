# Audit Prompt

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


## Security Context
# Security Context

Authentication & Isolation:
- Supabase Auth for token issuance.
- ES256 JWT verification in backend.
- Multi-tenancy: Every user-owned table has 'user_id' (NOT NULL).
- RLS policy: 'tenant_isolation' keyed on 'app.current_user_id' GUC.
- Ownership checks return 404 for missing or unauthorized resources.


## Investor Experience Context
# Investor Experience Context

Investor Trust & Clarity:
- Metric comprehension: Are units and calculations clear?
- Dashboard clarity: Mobile-first status at a glance.
- Investor trust: Presentation must build confidence; limitations must be clear.
- Presentation of insights: Language must be investor-friendly, not overly technical.


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
- **Cookie domain/scope risk, specific to this deployment.** Per prior session state, the frontend is reached via VM IP through a same-origin `/api` proxy, and the box's real IP recently changed (172.23.80.6 → 167.233.141.50 per earlier confirmation). This is the *first* time cookie-based session storage is being introduced (Supabase's client SDK previously owned token storage). Cookie `Domain`/`Secure`/`SameSite` settings need to be verified against however the app is actually being accessed today, not assumed from local dev — this is a plausible silent-failure point (login succeeds, cookie never gets sent back) that's easy to miss until manual testing.

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

## Implementation
## Implementation — manual, performed by Claude (2026-08-10)

Gemini's implementation run failed (`TerminalQuotaError` — daily free-tier quota exhausted, same
failure mode as O4/`feature-015`). Per SDLC.md's model-ownership fallback, the founder directed
Claude to implement directly and route QA to Qwen as originally planned. `status.yaml` still
records `model_implementation: gemini` as the original assignment for audit-trail honesty — this
note documents the actual execution path.

### Scope delivered
Full cutover per the final resolved `request.md`: custom bcrypt/HS256 auth (architecture-002
Phase 2) + a fresh, non-sandbox local Postgres target (Phase 3), no data migration (founder
explicitly disregarded existing Supabase data).

### Backend
- **Migration `b3f1a9c7d2e4`**: adds `users.email` + `users.password_hash`, creates
  `refresh_tokens` (hashed tokens only), drops RLS + policies on **all 10** tables that ever had
  it — including `manual_holdings`, added by a later migration than the original RLS rollout and
  easy to miss (caught by integration tests, not by inspection).
- **`app/core/auth.py`** — full rewrite: bcrypt password hashing, HS256 access tokens (cookie-read,
  not Bearer-header), opaque random refresh tokens (SHA-256 hashed at rest, rotated on every use),
  CSRF double-submit helpers, cookie set/clear helpers.
- **`app/api/auth.py`** (new) — `POST /auth/login` (IP rate-limited, constant-time-shaped failure
  path), `POST /auth/logout` (revokes refresh token), `POST /auth/refresh` (rotates), `GET
  /auth/me`, `bootstrap_admin_user()` (idempotent — guarded on "any user exists", not a specific
  email, so a restart can't silently reset the password).
- **`app/main.py`** — global CSRF middleware (double-submit, enforced only when a session cookie is
  present — an anonymous request has no session to hijack and falls through to the normal 401 gate
  instead of an incorrect 403), bootstrap call in `lifespan`, auth router registered.
- **`app/db/session.py`** — removed the RLS per-transaction GUC event listener (dead code once RLS
  is gone).
- **`app/api/assets.py`** — fixed a real bug the new schema surfaced: `_complete_onboarding` used
  to upsert-INSERT into `users`, which now violates the NOT NULL `password_hash` column for any
  caller without an existing row. Changed to a plain UPDATE — correct under the single-user model,
  where a `users` row always exists (created at bootstrap) before any authenticated request is
  reachable at all.
- **`requirements.txt`** — added `bcrypt`.

### Frontend
- Removed `@supabase/supabase-js` entirely (`package.json`, `lib/supabase.ts` deleted,
  `.env.local`'s Supabase vars removed).
- **`AuthProvider.tsx`** — rewritten: `GET /auth/me` on load, proactive refresh timer (10 min,
  under the 15 min access-token TTL) instead of Supabase's `onAuthStateChange`.
- **`LoginScreen.tsx`** — rewritten: single admin email/password form, Google OAuth button and
  signup mode removed (no multi-user signup in the single-user model — Google OAuth was already
  cancelled per `FEATURE-BACKLOG.md` P1).
- **`lib/api.ts`** — removed the Bearer-token `authHeaders()` (cookies now attach automatically on
  same-origin requests); added `csrfHeaders()`, wired into every mutating call site (`post`,
  `deleteAsset`, `importCsvDryRun`/`Confirm`); added `login`/`logout`/`getMe`/`refreshSession`.

### Infra
- **`docker-compose.local.yml`** (new) — distinct, non-sandbox Postgres container
  (`investment_tracker_postgres`, port `5433`), per the plan's explicit recommendation to keep the
  architecture-002 Phase 1 sandbox disposable rather than promoting it to hold real usage.
- **`db-init/01-create-app-user.sh`** — creates the least-privilege `app_user` role at container
  init, same pattern the integration-test fixture already used.
- **Incident during cutover**: bringing up `docker-compose.local.yml` without `-p` unexpectedly
  recreated/removed the sandbox container, because both compose files defaulted to the same
  directory-derived Compose project name. No data lost (sandbox held zero real rows, confirmed
  earlier in planning). Fixed: both compose files now document an explicit `-p` project name to
  prevent recurrence; sandbox container restored under `-p investment-tracker-selfhost`.

### Docs
- `docs/architecture/AUTH.md` rewritten for the new design.
- New ADR `0005-custom-auth-single-user.md`; ADRs `0002` (Supabase Auth) and `0003` (RLS backstop)
  marked superseded, kept for historical record — not deleted.
- Broader doc sweep (SECURITY-AUDIT.md, DEPLOY.md, BACKUP-RESTORE.md, etc. still reference
  Supabase/RLS in places) explicitly **out of scope** for this task — flagged as follow-up, not
  silently expanded into.

### Cutover, executed live
1. Generated `JWT_SECRET` (32-byte hex), Postgres admin/app-user passwords, `ADMIN_PASSWORD`.
2. `docker compose -f docker-compose.local.yml up -d` — new container healthy.
3. `alembic upgrade head` against it — full chain applied cleanly (12 tables, RLS off everywhere,
   `app_user` role present — verified via direct `psql` queries, not assumed).
4. `backend/.env` repointed: `DATABASE_URL`/`ADMIN_DATABASE_URL` → new container, `DB_SSL=`
   (no TLS locally), Supabase vars removed, new auth vars added.
5. Backend restarted — bootstrap log confirmed: `auth.bootstrap.created_admin
   email=nrsubramanya77@gmail.com`.
6. Frontend rebuilt (`npm run build`, picks up the Supabase-SDK removal) and restarted.


## Code Review
<!-- Artifact template: code review findings -->


## QA
## QA — manual, performed by Claude (2026-08-10)

Qwen's QA run failed (`OpenRouter API 401: "User not found"` — the API key itself appears invalid/
revoked, not a transient quota issue like Gemini's earlier failure). Founder directed Claude to
perform QA directly rather than wait on the external service.

### Automated suite — fresh run, both tiers
- **Unit**: 92 passed, 0 failed.
- **Integration** (real Postgres via testcontainers, full Alembic chain applied fresh): 119 passed,
  0 failed.
- Covers the required set: login, token expiry/refresh, revocation, bootstrap idempotency,
  ownership checks (`test_auth_isolation.py`, `test_tenant_isolation.py` — unaffected by the auth
  swap, still passing against app-layer-only filtering), CSRF, and a negative test proving an old
  Supabase-style ES256 token is rejected post-cutover.

### Live adversarial testing against the actual cut-over instance (not just the test suite)
Run directly against the running backend (`127.0.0.1:8000`) and through the frontend's same-origin
`/api` proxy (`127.0.0.1:3000`) — the real request path, not a mocked one.

| # | Check | Result |
|---|---|---|
| 1 | No cookie on a protected endpoint | 401 ✅ |
| 2 | Wrong password | 401 ✅ |
| 3 | Old-style `Authorization: Bearer` header (the pre-cutover pattern) | 401 — cookie-only auth confirmed, old path is actually gone ✅ |
| 4 | `/health` public, no auth | 200 ✅ |
| 5 | Repeated failed logins → rate limit | 429 after threshold ✅ |
| 6 | Cookie flags on login | `access_token`: `HttpOnly; SameSite=lax; Path=/`. `refresh_token`: `HttpOnly; SameSite=lax; Path=/auth` (scoped, reduces exposure). `csrf_token`: **not** HttpOnly (required — JS must read it), `SameSite=lax`. No `Secure` flag on any — correct, `COOKIE_SECURE=false` for plaintext-HTTP-by-default per the O5 decision ✅ |
| 7 | Mutating request, valid session, no CSRF header | 403 ✅ |
| 8 | Mutating request, valid session, wrong CSRF header | 403 ✅ |
| 9 | Mutating request, valid session, correct CSRF header | 200 ✅ |
| 10 | Refresh → new access+refresh+csrf tokens issued, refresh value actually changes | rotated ✅ |
| 11 | Reuse of the just-rotated (old) refresh token | 401 — reuse detected, not silently accepted ✅ |
| 12 | Logout | 200 ✅ |
| 13 | Refresh using the just-logged-out token | 401 — revocation confirmed ✅ |
| 14 | Exactly one `users` row after all of the above (bootstrap idempotency held under repeated backend restarts during cutover) | 1 ✅ |
| 15 | No orphaned active refresh tokens left over from testing | cleaned up (revoked), 0 active ✅ |

Also verified during the cutover itself (not repeated here): schema has all 12 tables, RLS
`relrowsecurity = f` on every one of them (checked directly via `pg_class`, not assumed from the
migration's intent), `app_user` role exists, end-to-end asset create/list/delete through the real
frontend proxy.

### Not independently verified — carried forward, not blocking
- **Real browser session** (cookie persistence across page loads, `AuthProvider`'s proactive
  refresh timer firing correctly over a long-lived tab) — only curl-level HTTP checks were done,
  not an actual browser. Recommend a real login through the browser before considering this fully
  closed.
- **Supabase Auth allowed-origins** question from the original O4 planning is now moot — Supabase
  Auth is gone entirely, not just the DB.
- **Cookie behavior specifically over the Tailscale HTTPS origin** vs. the plaintext IP path — both
  *should* work identically (cookies aren't `Secure`, so both HTTP and HTTPS accept them; same-origin
  proxying means no `Domain` mismatch either way) but wasn't tested from an actual device on each
  path.

### Addendum (post first audit pass) — items closed
- **Admin recovery path** (Planning item 5, flagged as silently dropped) — written:
  `docs/runbooks/ADMIN-ACCOUNT-RECOVERY.md`, linked from `docs/INDEX.md`.
- **Refresh-token field completeness** (audit flagged as "unverified rather than confirmed") —
  checked directly via `\d refresh_tokens`: `expires_at`, `revoked_at`, `created_at`,
  `last_used_at` all present, exactly as Planning specified. Was a documentation gap in this file,
  not a code gap.
- **Cookie/access-path verification against the real environment** (Planning item 6, audit's
  sharpest finding) — closed for real: login + session check now verified end-to-end via `curl`
  against both `http://167.233.141.50:3000` (the real public IP) and
  `https://madhyastha-lab-server.tail40a80c.ts.net` (the real Tailscale URL), not just `127.0.0.1`.
  Both work correctly.
- **`COOKIE_SECURE=false` on a public-IP-reachable box** (audit's new-risk finding) — not fixed
  (that would mean reopening the O5 decision), but now explicitly documented in `AUTH.md`'s open
  items with the accurate framing: not a *new* exposure (the old Supabase Bearer token traveled the
  same plaintext path), but auth is now the *sole* boundary rather than one of two. Founder's call
  on whether/when to revisit, not something to silently fix or silently leave undocumented.
- **Compose project-name collision** — third compose file (`docker-compose.yml`) checked; defines
  no Postgres service so can't collide by service name, but given the explicit `-p` guidance for
  consistency anyway since it's not impossible to misuse.

### Verdict
**Pass.** 211 automated tests, 15 live adversarial checks, all green. Two real bugs were caught and
fixed during this work (not pre-existing, both introduced by the schema change and caught before
reaching production): `manual_holdings` RLS omission (integration tests), `_complete_onboarding`'s
NOT-NULL violation on upsert-insert (integration tests). Neither would have been caught by code
inspection alone.

