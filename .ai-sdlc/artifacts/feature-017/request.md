# Feature Request: Full Cutover — Custom Auth Rewrite + Fresh Local Postgres (Supabase → Local Postgres)

## User Request

Originally "change db from supabase to local postgres container." Resolved through discussion to
a **full cutover, fresh start**: custom auth rewrite (`architecture-002` Phase 2) + a fresh local
Postgres instance (schema only, via existing Alembic chain) — **no migration of existing Supabase
data**. Founder explicitly does not care about preserving current user data.

## Context — verified against actual live state, not memory (twice)

Two founder beliefs about current state were checked directly against the live VM and code, and
both turned out to be wrong:

1. **"DB is already local Postgres"** — false. `backend/.env`'s `DATABASE_URL` still points at
   Supabase (`aws-1-ap-southeast-1.pooler.supabase.com`), confirmed as what the live `uvicorn`
   process actually loads. The running Docker Postgres container
   (`investment_tracker_selfhost_postgres`) is the isolated Phase 1 sandbox — correct schema,
   zero rows.
2. **"Auth rewrite is already done"** — also false. `backend/app/core/auth.py` still verifies via
   `PyJWKClient(settings.supabase_jwks_url, ...)` — pure Supabase JWKS verification. No
   `bcrypt`/`passlib` anywhere in `backend/app`. The `users` table has no `password_hash` column.
   RLS is still active (`tenant_isolation` policy present) — supposed to be ripped out under
   Phase 2 per the `architecture-002` decision record, hasn't been.

## Resolved decisions (this session, founder-explicit)

1. **Scope: full cutover now** — custom auth system (bcrypt/JWT, RLS removal) + fresh local
   Postgres, together.
2. **No data migration.** Founder does not care about the existing Supabase user data — this
   **removes** the need for a data migration mechanism, row-count/integrity verification, and the
   "migration must stay read-only until final repoint" rollback design entirely. This is a
   materially simpler, lower-risk task than the data-migration version originally scoped: there is
   no real data whose loss is a risk, because nothing is being carried over. **Existing Supabase
   data is left as-is, untouched, not actively deleted** — abandoned in place, available later if
   anyone ever wants to look at it, but out of scope for this task either way.
3. Given (2), the earlier backup-gate discussion is now moot for *this* task specifically — there's
   no real-data operation to back up against. (Backup automation, `O1`/`feature-016`, remains a
   real and separate priority for protecting whatever *new* data gets written into local Postgres
   going forward, post-cutover — not a blocker for this task.)

## Auth design — carry forward already-CEO-approved decisions, don't re-decide

`architecture-002`'s original request/decision record (approved 2026-07-30, restated in
`ROADMAP.md` step 5) already settled the auth design. Implementation should follow this, not
reopen it:

- HS256 JWT with a generated secret in `.env` (explicit downgrade from current ES256/JWKS,
  already accepted given the self-hosted single-user threat model)
- httpOnly cookie token storage, with CSRF protection (SameSite + CSRF token on state-changing
  requests)
- Short-lived access token + server-tracked, **revocable** refresh token (logout/password-change
  revocation) — stateless-only JWTs were explicitly rejected at planning time because they can't
  be revoked
- First-run bootstrap via `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars — no signup flow, no setup
  wizard (single-user model)
- No email/SMTP password reset — admin resets via `.env`/DB + restart
- RLS policies removed entirely (single fixed user, no longer needed — also closes the dormant
  "misconfigured policy" footgun flagged at pivot-planning time)
- **Test coverage is a required completion condition, not deferred**: login, token expiry/refresh,
  revocation, bootstrap, ownership checks — per `ROADMAP.md` step 5's explicit requirement

## Fresh local Postgres — what's actually needed now (simplified from the earlier migration framing)

1. **Target container**: stand up a distinct, non-sandbox Postgres container for the real cutover
   (recommended in this workflow's earlier planning pass, still applies) — keep
   `investment_tracker_selfhost_postgres` as a disposable test target, don't collapse "thing I
   test against" and "thing that holds live data" into one container.
2. **Schema only**: run the existing Alembic chain against the new container (already proven to
   work cleanly in `architecture-002` Phase 1) — no data import step.
3. **New migration for auth changes**: `password_hash` on `users`, refresh-token table, RLS
   policy removal — lands on top of the existing chain.
4. **Cutover sequence**: stop backend → repoint `DATABASE_URL`/`ADMIN_DATABASE_URL` at the new
   container → repoint auth config (new `JWT_SECRET`, drop `SUPABASE_JWKS_URL`/`SUPABASE_ISSUER`)
   → run first-run bootstrap (`ADMIN_EMAIL`/`ADMIN_PASSWORD`) → restart → smoke test (login,
   dashboard loads, add/view an asset).
5. **HA trade-off still applies, independent of the data question**: moving off Supabase-managed
   Postgres means losing whatever managed durability/failover Supabase provided for whatever data
   accumulates from this point forward. Worth naming so it's a conscious tradeoff, not a surprise.

## What this touches

- `backend/app/core/auth.py` — full rewrite (Supabase JWKS verification → custom bcrypt/JWT)
- `backend/app/db/models.py` + new Alembic migration — `password_hash` on `users`, refresh-token
  table, RLS policy removal
- `backend/.env` — `DATABASE_URL`/`ADMIN_DATABASE_URL` repointed to the new local container, new
  `JWT_SECRET`, `ADMIN_EMAIL`/`ADMIN_PASSWORD` added, Supabase auth vars removed
- Frontend — login flow changes (cookie-based session instead of Supabase client SDK), CSRF
  token wiring on state-changing requests
- Existing Supabase data — untouched, abandoned in place, not migrated, not deleted as part of
  this task

## Final implementation decisions (resolved this session)

Both open items from `planning.md`'s security review are now resolved:

1. **CSRF mechanism: double-submit cookie.** A readable CSRF cookie compared against a matching
   header on state-changing requests. (Not a synchronizer token / server-side session state.)
2. **Cookie `Secure` flag: configurable via `COOKIE_SECURE` env var, default `false`.** Login must
   work out-of-the-box over plain HTTP — both the founder's own plaintext `:3000` access path (per
   the `O5` decision to keep it open for self-hosters) and any self-hoster's zero-config
   `docker-compose up` over `localhost`/LAN. A hardcoded `Secure: true` would silently break login
   on any non-HTTPS path, since browsers refuse to send `Secure` cookies over plain HTTP.
   Self-hosters who put real HTTPS in front (the founder's own Tailscale URL, or a future domain)
   can opt in via `COOKIE_SECURE=true` in their own `.env` for stronger protection — this should be
   called out in the self-host README (`ROADMAP.md` step 8). `httpOnly` and `SameSite` stay
   unconditional (not HTTPS-dependent), only `Secure` is toggled.

The remaining items from `planning.md`'s "open items to resolve" list (refresh-token field spec,
bootstrap idempotency guard, login rate-limiting, manual recovery-path doc, full Supabase SDK
removal, smoke-test-as-hard-rollback-gate) are accepted as stated — straightforward best practice,
no further founder decision needed on those.

## Constraints / governance

- Auth model, database schema, migrations, and infrastructure — all independently CEO-gated per
  `CLAUDE.md`; this request combines all four categories. Founder's direct, explicit decisions in
  this session (full scope, no data migration, existing data disregarded) constitute that approval
  for what's described here.
- Since there's no real-data operation, the earlier "split into two checkpointed sub-stages"
  recommendation is worth revisiting in this pass — planning should say whether it still applies
  (e.g., still testing auth against the fresh container before declaring done) or whether the
  simplified scope makes a single implementation pass reasonable.
