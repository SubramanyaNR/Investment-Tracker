# 0005 — Custom bcrypt/HS256 auth, single-user, RLS removed

- Status: Accepted
- Date: 2026-08-10

## Context
`architecture-002` (2026-07-30) pivoted WealthSignal from hosted multi-tenant SaaS to an
open-source, self-hosted, single-user project. Supabase Auth (`0002`) and the RLS multi-tenancy
backstop (`0003`) were both designed for a hosted, potentially-multi-tenant model that no longer
applies, and both introduce a dependency (Supabase reachability) or complexity (dual DSNs, role
provisioning, per-request GUC) with no remaining benefit once there is exactly one user.

## Decision
Replace Supabase Auth with self-issued auth against the local Postgres `users` table:
- **Password hashing:** bcrypt (`backend/app/core/auth.py`).
- **Tokens:** HS256 JWT, high-entropy secret generated once into `.env` (`JWT_SECRET`) — no
  external JWKS verifier exists anymore, so ES256/JWKS added complexity with no longer any payoff.
- **Session storage:** httpOnly cookies (`access_token`, short-lived; `refresh_token`, longer-lived
  and path-scoped to `/auth`) instead of a client-held Bearer token.
- **CSRF:** double-submit cookie (`csrf_token`, JS-readable, echoed as `X-CSRF-Token` on
  state-changing requests) — enforced globally in middleware, but only when a session cookie is
  present; an anonymous request has no ambient authority to hijack and falls through to the normal
  401 auth gate instead.
- **Refresh token revocation:** server-tracked (`refresh_tokens` table, hashed value only), rotated
  on every use — reuse of an already-consumed or stolen token is detectable, not just rejected.
- **Cookie `Secure` flag:** `COOKIE_SECURE` env var, default `false` — login must work over plain
  HTTP out of the box (self-host `docker-compose up`, zero setup) per the O5 decision
  (`FEATURE-BACKLOG.md`); opt into `true` when serving behind real HTTPS (e.g. the founder's own
  Tailscale URL).
- **Bootstrap:** first-run only, idempotent (guarded on "any user exists", not a specific email) —
  creates the single admin user from `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars. No signup flow.
- **Password reset:** none — admin resets via `.env`/DB + restart (documented in a runbook, not
  built as a feature), since there's no mail service in a self-hosted single-user install.
- **RLS removed entirely** — all tenant_isolation policies dropped (`b3f1a9c7d2e4`), across every
  table that ever had one, including `manual_holdings` (added by a later migration than the
  original RLS rollout, easy to miss). The app-layer `WHERE user_id = ...` filter is unchanged and
  is now the sole enforcement mechanism — acceptable because a forgotten filter in a single-user
  system has no other tenant to leak to.
- **`app_user` role kept** — least-privilege DB access is still worthwhile independent of RLS; only
  the RLS policies themselves were dropped, not the role split.

## Consequences
- No more Supabase dependency for auth (or anything else) — the stated goal of `architecture-002`.
- Trades Supabase's managed key rotation/OAuth/email-confirmation for code this project now owns
  and must maintain — accepted per the build-vs-buy reversal already made in `architecture-002`'s
  broader decision to self-host.
- Revocation is now possible (server-tracked refresh tokens) — a real improvement over `0002`'s
  "no revocation until token expiry" limitation (M4).
- Losing RLS as a backstop is a real, accepted reduction in defense-in-depth — correct for exactly
  one tenant, but if this project ever became multi-tenant again, RLS (or an equivalent) would need
  to come back, not be assumed unnecessary by default.
- `COOKIE_SECURE=false` by default means session cookies can be read by anyone with network access
  to an unencrypted HTTP session for whoever hasn't put HTTPS in front of their instance — a
  conscious, documented trade for zero-setup self-host onboarding, not an oversight.

## Amendment (secure-001 / feature-020, 2026-08-20): auth can be disabled entirely

Added `AUTH_ENABLED` (default `false`), letting login be skipped entirely for single-device
self-host convenience — a further, deliberate reduction of this ADR's auth boundary, going beyond
`COOKIE_SECURE=false` to no credential check at all. Full design and threat model in
`docs/architecture/AUTH.md` ("Auth-disable toggle"); the short version: every request resolves to
the one bootstrapped admin user (never anonymous), there is no in-app way to flip the flag (env +
restart only, to avoid a pre-auth-reachable control that could disable its own gate), and a warning
banner shows on every page whenever auth is off, with no default able to silently suppress it.
