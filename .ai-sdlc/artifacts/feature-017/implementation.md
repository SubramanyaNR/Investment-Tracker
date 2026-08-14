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
   email=admin@example.com`.
6. Frontend rebuilt (`npm run build`, picks up the Supabase-SDK removal) and restarted.
