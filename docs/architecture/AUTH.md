# Authentication & multi-tenancy design

> The WHY + shape of auth. For per-decision rationale see
> `decisions/0005-custom-auth-single-user.md` (current) and `decisions/0002-supabase-auth-es256.md`
> / `decisions/0003-rls-app_user-backstop.md` (superseded, historical record).

## Shape
- **Provider:** self-issued, against the local Postgres `users` table — no external identity
  provider. Single-user model: no signup flow, one admin account created at first-run bootstrap.
- **Frontend:** `AuthProvider` calls `GET /auth/me` on load and gates the app; `lib/api.ts` no
  longer attaches any auth header — the httpOnly session cookie is sent automatically by the
  browser on same-origin requests via the `/api` proxy. Only the CSRF token (non-httpOnly, by
  design) is read client-side and echoed as `X-CSRF-Token` on mutating requests.
- **Backend AuthN:** `backend/app/core/auth.py` → `get_current_user_id` reads the `access_token`
  httpOnly cookie, verifies it as an HS256 JWT signed with `JWT_SECRET`. No JWKS, no network call —
  pure local verification.
- **Identity source:** the JWT `sub` claim **only**. No Pydantic model exposes `user_id`; clients
  cannot inject identity.
- **Session lifecycle:** short-lived access token (`ACCESS_TOKEN_TTL_SECONDS`, default 15 min) +
  longer-lived, server-tracked refresh token (`refresh_tokens` table, hashed value only, rotated on
  every use via `POST /auth/refresh`). `AuthProvider` refreshes proactively on a timer so an open
  tab never hits a hard expiry. Logout (`POST /auth/logout`) revokes the refresh token — real
  revocation, unlike the old Supabase-JWT stateless-verify model.
- **CSRF:** double-submit cookie, enforced in global middleware (`app/main.py`), but only when an
  `access_token` cookie is present — an anonymous request has no session to hijack and falls
  through to the normal 401 gate instead of a CSRF 403.
- **Bootstrap:** `bootstrap_admin_user()` runs in `lifespan` on every startup; idempotent (guarded
  on "any row exists in `users`", not a specific email) — a container restart never resets the
  admin password.

## Multi-tenancy — single line of defense, by design
This is a single-user system; the multi-tenant RLS backstop (`0003`) was removed entirely
(migration `b3f1a9c7d2e4`), not kept dormant. **App-layer filtering is the sole enforcement
mechanism**: every user-owned table has a `user_id` (NOT NULL); every query carries
`WHERE user_id == sub`. This is a deliberate, accepted reduction in defense-in-depth — correct for
exactly one tenant. If this project ever became multi-tenant again, RLS (or an equivalent) would
need to come back, not be assumed unnecessary by default.

The `app_user` least-privilege DB role is kept regardless — it limits blast radius at the DB layer
independent of RLS. Migrations + the scheduler use a separate **admin** connection
(`ADMIN_DATABASE_URL`, superuser).

## Invariants (do not break)
- Never trust a client-provided `user_id`; derive it from the verified access-token cookie.
- Ownership checks return 404 (not 403) for another user's resource — don't leak existence.
- `POST /assets` merge-by-`scheme_code`/`coingecko_id` is scoped per user.
- Public surface is intentional and minimal: `/health`, `/market/*`, `POST /auth/login`.
- Every query on a user-owned table **must** filter by `user_id` explicitly — there is no RLS
  backstop anymore; a missed filter is a real, unguarded leak, not just a defense-in-depth gap.
- Refresh tokens are stored **hashed only** (SHA-256, deterministic — these are high-entropy random
  values, not low-entropy passwords, so a fast keyed hash for DB lookup is correct, not bcrypt).
- `COOKIE_SECURE` defaults to `false` so login works out of the box over plain HTTP (self-host
  `docker-compose up`, zero setup) — set `true` only when real HTTPS is actually in front (see
  `decisions/0005-custom-auth-single-user.md`).

## Auth-disable toggle (secure-001 / feature-020)

- **`AUTH_ENABLED`** (default `false`): when off, `get_current_user_id`
  (`backend/app/core/auth.py`) skips the JWT check entirely but still resolves
  every request to the single bootstrapped admin user, fetched from the DB and
  cached in memory — never null, never client-supplied, never a second user.
  This is the single choke point; no router has its own auth-bypass logic.
- **`GET /auth/status`** (public, unauthenticated) returns `{auth_enabled}` so
  the frontend can render a warning banner even before login. It's
  intentionally public — it discloses only what the banner itself already
  would once rendered.
- **The banner shows whenever `AUTH_ENABLED=false`, full stop**, with a single
  fixed wording — no local-vs-hosted variant. Two earlier designs were tried
  and rejected: first, a `deployment_context` var that could suppress the
  banner entirely on `local` (rejected as a double-negative gap — forgetting
  to set *both* vars correctly would give zero warning); then a version where
  `deployment_context` only softened the wording rather than suppressing it
  (rejected too — deployment topology, e.g. Tailscale-only access, is
  genuinely ambiguous, so there's no wording distinction worth making;
  always showing the strongest copy is simpler and never wrong).
- **No in-app write path exists to toggle `AUTH_ENABLED`.** It's an env var +
  restart, on purpose — a control that could disable the only access gate,
  reachable from the same surface that gate is supposed to protect, is a
  tamper/persistence risk. The homescreen only *displays* current state.
- **Credential changes go through `make reset-admin-password` only** —
  updates the existing single user row in place (email/password) and revokes
  every outstanding refresh token. `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env`
  remain first-boot-only, unchanged from before this work.
- **Deliberately not added: `token_version`/access-token revocation.** The
  original security remediation plan (`secure-001`) called for a token-version
  column checked on every request so a password reset would invalidate
  already-issued access tokens immediately. Implemented instead: `reset-admin-
  password` revokes all refresh tokens (existing mechanism, no schema change),
  bounded by the access token's existing 15-minute TTL — the same exposure
  window a normal logout already has today, since logout doesn't invalidate a
  still-valid access token either. Chosen over a schema migration + per-
  request DB check because it preserves the documented "pure local
  verification, no network call" property of access-token checks, which a
  `token_version` check would have broken. Revisit if the 15-minute window
  proves too wide in practice.
- **Full data continuity across disable → enable is guaranteed by construction**:
  `bootstrap_admin_user()` creates the one user row on the very first startup
  regardless of `AUTH_ENABLED`, and the disabled-mode bypass resolves to that
  same row — so data added while disabled is already under the same user_id
  you'll log into once auth is turned on.

## Known open items
- No brute-force lockout beyond the per-IP rate limit on `/auth/login` (`rl_login_attempts`,
  default 5/60s) — adequate for a single-user personal instance, revisit if that changes.
- **Locked-out admin recovery**: no email reset (no mail service) — see
  `../runbooks/ADMIN-ACCOUNT-RECOVERY.md` for the direct-DB-edit path.
- **Cookies travel in plaintext on the public-IP path.** Verified 2026-08-10: login works
  end-to-end both via the plaintext public IP (`http://<vps-ip>:3000`) and the Tailscale
  HTTPS URL — same-origin `/api` proxying means no explicit cookie `Domain` is needed either way.
  But `COOKIE_SECURE=false` means the plaintext path sends `access_token`/`refresh_token` in the
  clear over the public internet — anyone on-path between a client and this VM could capture an
  active session. This isn't a new exposure introduced by this cutover (the old Supabase Bearer
  token traveled the same plaintext path, same risk), but it's now the *entire* auth boundary
  rather than one of two (Supabase no longer independently manages sessions). Accepted for now
  as a consequence of the O5 decision (`FEATURE-BACKLOG.md`) to keep port 3000 open by default;
  worth an explicit, conscious re-check once/if that decision is revisited.
