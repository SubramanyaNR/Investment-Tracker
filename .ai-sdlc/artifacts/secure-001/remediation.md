# Remediation Plan: auth-toggle

Workflow: secure-001 | Stage: remediation

Addresses findings from `assessment.md`. Ordered by severity/dependency, not necessarily implementation order (item 1 is a prerequisite for 3 and 4).

## R1 — Single choke-point bypass (closes T2)

Implement the `AUTH_ENABLED=false` bypass **inside** `get_current_user_id` (`backend/app/core/auth.py`) and/or `get_session` (`backend/app/api/deps.py`) — not per-router. Logic:

```
if settings.auth_enabled:
    # existing behavior: verify JWT cookie, raise 401 on failure
else:
    # fetch the single bootstrapped user id from DB (SELECT id FROM users LIMIT 1)
    # never from request headers, query params, or any client-supplied value
    # raise 500 (not a silent anonymous mode) if no user row exists yet
```

No other router file changes. This bounds the blast radius of a mistake to one function and keeps the "exactly one user_id, always" invariant enforced in exactly one place, matching how `get_session` already stamps `request.state.user_id` today.

**Acceptance**: grep confirms no router does its own `if AUTH_ENABLED` check; a request with a forged/absent cookie under `AUTH_ENABLED=false` still resolves to the real admin user_id, never a spoofed one.

## R2 — CLI-only `make reset-admin-password` with session invalidation (closes T4, T5)

- New `Makefile` target invoking a backend script (e.g. `backend/scripts/reset_admin_password.py`), run via `docker compose exec` or direct python — **not** an HTTP route, not importable from any router.
- Script prompts interactively for new password (no plaintext password as a bare CLI arg, to avoid shell-history/process-list leakage); optionally allows updating email.
- Updates `password_hash` (and `email` if provided) on the existing single user row in place.
- Must invalidate existing sessions issued under the old credentials. Check current JWT design (`backend/app/core/auth.py`) for expiry length; if long-lived/no server-side revocation exists, add a minimal token-versioning field (e.g. `users.token_version` incremented on reset, checked against JWT claim) rather than building a full session store — smallest change that closes T5.

**Acceptance**: script only runs via `make`/CLI; a JWT issued before a reset fails authentication after the reset; password never appears in shell history or application logs.

## R3 — Authenticated-only homescreen toggle (closes T3)

- The enable/disable control for `AUTH_ENABLED` is a **runtime env concern**, not a DB-backed setting — flipping it requires editing the deploy env and restarting (this was already implied by "env flag" in `request.md`). Clarify in remediation: there is no separate "in-app toggle that writes to the DB and takes effect without restart" — that would reintroduce T3 in a different form (an authenticated user could still leave it toggled from a prior session). Instead, the "homescreen" surface is **informational + instructional**: it shows current `AUTH_ENABLED` state and, if disabled, explains how to enable it (env var + restart), gated behind the existing authenticated session when auth is on, and behind nothing when auth is off (since there's no session to gate behind in that state — consistent with T1 being an accepted, bounded tradeoff, not something this control can fix).
- This resolves T3 more simply than the original design (an authenticated in-app write path): there's no mutable, tamperable in-app state to protect, because the flag lives in the env, not the DB.

**Acceptance**: `AUTH_ENABLED` has no corresponding DB row or API write path; the homescreen surface is read-only display + instructions.

## R4 — Explicit `DEPLOYMENT` env var for danger banner (closes reliability concern)

- New env var, e.g. `DEPLOYMENT_CONTEXT=local|hosted`, set once by the deployer (same pattern as `ADMIN_EMAIL`), defaulting to `local` to avoid nagging the common single-machine case unnecessarily — but combined with `AUTH_ENABLED=false` as the actual trigger condition:
  - `AUTH_ENABLED=false` + `DEPLOYMENT_CONTEXT=hosted` → prominent, persistent banner: "Authentication is disabled on a hosted deployment. Anyone who can reach this server has full access to your portfolio data."
  - `AUTH_ENABLED=false` + `DEPLOYMENT_CONTEXT=local` (default) → no banner, or a much quieter one-line note.
- No request-origin/Host-header heuristics, per assessment's reliability finding.
- Document in `.env.example` and `docs/architecture/AUTH.md` what `DEPLOYMENT_CONTEXT=hosted` means and when to set it (any VPS, cloud box, or anything reachable outside the operator's own machine/LAN — explicitly including Tailscale-only setups, since that's still "more than one device can reach this").

**Acceptance**: banner logic is a pure function of two env vars, no runtime detection; docs explicitly tell the deployer when to flip `DEPLOYMENT_CONTEXT`.

## R5 — Onboarding nudge for credential rotation (closes T6)

- `.env.example` ships obviously-fake placeholder `ADMIN_EMAIL`/`ADMIN_PASSWORD` (e.g. `changeme@example.com` / a value that fails a basic strength check) rather than any usable default.
- README / `docs/runbooks/LOCAL-DEV.md` (or DEPLOY.md) gets a short section: "First-time setup: run `make reset-admin-password` before enabling auth or exposing this instance."
- No code enforcement beyond the docs nudge — keeps scope tight, consistent with change-discipline (don't add complexity, e.g. forced-password-change flows, beyond what's needed).

**Acceptance**: docs updated; `.env.example` placeholder is unambiguous.

## Out of scope for this workflow (recorded, not fixed here)

- Multi-user support / true multi-tenancy — not applicable, system remains single-user by design (ADR 0005).
- Full session-store/revocation infrastructure — R2's minimal token-versioning approach is the smallest fix that closes T5; a full session store is unwarranted complexity for a single-user app.
- Any change to `bootstrap_admin_user()`'s first-boot-only semantics — explicitly preserved per `request.md`.

## Governance checkpoint

R1–R5 collectively implement the auth-model change flagged in `assessment.md` as requiring CEO sign-off, specifically: **accepting T1 (full unauthenticated access during the disabled window) as a permanent, by-design tradeoff**, bounded by R3/R4 rather than eliminated. Recommend explicit acknowledgment of this at approval, not just approval of the engineering tasks.

## Summary of work items for implementation stage

1. `backend/app/core/auth.py` / `backend/app/api/deps.py`: `AUTH_ENABLED` bypass, single choke point (R1)
2. `backend/scripts/reset_admin_password.py` + `Makefile` target + minimal `token_version` field/check (R2)
3. Frontend: read-only auth-status display on homescreen, no write path (R3)
4. `DEPLOYMENT_CONTEXT` env var + banner component, docs (R4)
5. `.env.example` placeholder hardening + README/runbook section (R5)
6. `docs/architecture/AUTH.md` update / superseding note to ADR 0005 reflecting the new model
