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

## Known open items
- No brute-force lockout beyond the per-IP rate limit on `/auth/login` (`rl_login_attempts`,
  default 5/60s) — adequate for a single-user personal instance, revisit if that changes.
- **Locked-out admin recovery**: no email reset (no mail service) — see
  `../runbooks/ADMIN-ACCOUNT-RECOVERY.md` for the direct-DB-edit path.
- **Cookies travel in plaintext on the public-IP path.** Verified 2026-08-10: login works
  end-to-end both via the plaintext public IP (`http://167.233.141.50:3000`) and the Tailscale
  HTTPS URL — same-origin `/api` proxying means no explicit cookie `Domain` is needed either way.
  But `COOKIE_SECURE=false` means the plaintext path sends `access_token`/`refresh_token` in the
  clear over the public internet — anyone on-path between a client and this VM could capture an
  active session. This isn't a new exposure introduced by this cutover (the old Supabase Bearer
  token traveled the same plaintext path, same risk), but it's now the *entire* auth boundary
  rather than one of two (Supabase no longer independently manages sessions). Accepted for now
  as a consequence of the O5 decision (`FEATURE-BACKLOG.md`) to keep port 3000 open by default;
  worth an explicit, conscious re-check once/if that decision is revisited.
