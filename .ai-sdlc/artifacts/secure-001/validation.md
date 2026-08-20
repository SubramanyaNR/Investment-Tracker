# Validation Checklist: auth-toggle

Workflow: secure-001 | Stage: validation

This checklist validates the R1–R5 items from `remediation.md` once implementation exists. **Nothing has been implemented yet** — this is the acceptance criteria implementation must satisfy, produced ahead of time so `/feature` implementation work has a clear target and QA has a clear script.

## R1 — Single choke-point bypass

- [ ] `grep -rn "AUTH_ENABLED\|auth_enabled" backend/app/api/` returns hits only in `backend/app/core/auth.py` and/or `backend/app/api/deps.py` — no per-router conditionals.
- [ ] With `AUTH_ENABLED=false` and no `access_token` cookie sent: any endpoint (e.g. `GET /assets`) returns 200 with the real admin's data, not 401 and not empty/anonymous data.
- [ ] With `AUTH_ENABLED=false`, send a forged cookie or header claiming a different user_id (e.g. a random UUID) — response still resolves to the real single admin user_id (fetched server-side from DB), not the attacker-supplied value.
- [ ] With `AUTH_ENABLED=false` and the `users` table empty (fresh DB, before first boot completes) — endpoint returns 500, not a silent anonymous/null-user response.
- [ ] With `AUTH_ENABLED=true` (default-safe path unchanged): missing/invalid cookie still returns 401 exactly as today. Existing auth test suite passes unmodified.

## R2 — `reset-admin-password` + session invalidation

- [ ] `make reset-admin-password` is not reachable via any HTTP route — `grep -rn "reset_admin_password\|reset-admin-password" backend/app/api/` returns no router registrations.
- [ ] Running the script prompts interactively for the new password; the new password does not appear as a bare CLI argument, in `ps aux` output during the run, or in `.bash_history`/shell history afterward.
- [ ] After running the script, a JWT issued *before* the reset fails authentication on the next request (401), confirming `token_version` (or equivalent) is checked.
- [ ] After the reset, logging in with the new credentials succeeds and issues a JWT that passes the (now-current) token_version check.
- [ ] Script updates the existing single user row in place — no new row created, `SELECT count(*) FROM users` unchanged before/after.

## R3 — Read-only homescreen auth-status display

- [ ] No DB column, table, or migration exists for a mutable "auth enabled" setting — `AUTH_ENABLED` is read from process env only (`grep -rn "AUTH_ENABLED" backend/app/core/config.py` or equivalent settings module).
- [ ] No frontend API call exists that writes/toggles auth state (`grep -rn "auth.*enabled\|AUTH_ENABLED" frontend/lib/api.ts` shows no POST/PUT/PATCH).
- [ ] Homescreen displays current state (enabled/disabled) and, when disabled, plain-language instructions to enable (env var + restart) — verified visually in browser.
- [ ] The status display itself does not require authentication to view (consistent with there being no session to gate it behind when auth is off), but performs no state-changing action.

## R4 — `DEPLOYMENT_CONTEXT` danger banner

- [ ] `AUTH_ENABLED=false` + `DEPLOYMENT_CONTEXT=hosted` → banner renders prominently on every page (not just homescreen), persists across navigation, cannot be permanently dismissed (session-dismiss at most).
- [ ] `AUTH_ENABLED=false` + `DEPLOYMENT_CONTEXT=local` (default) → no prominent banner, or clearly de-emphasized note only.
- [ ] `AUTH_ENABLED=true` (any `DEPLOYMENT_CONTEXT`) → no danger banner regardless of context.
- [ ] No request-origin/Host-header/client-IP based logic exists anywhere in the banner code path — confirmed by code read, not just testing (a heuristic could pass tests in dev and still be wrong in production topology).
- [ ] `.env.example` and `docs/architecture/AUTH.md` document `DEPLOYMENT_CONTEXT`, including explicit guidance that Tailscale-only access still counts as "hosted."

## R5 — Onboarding / credential hardening

- [ ] `.env.example` `ADMIN_PASSWORD` placeholder is obviously non-usable (e.g. `changeme`) rather than a real-looking default.
- [ ] README or `docs/runbooks/LOCAL-DEV.md`/`DEPLOY.md` contains an explicit "run `make reset-admin-password` before enabling auth or exposing this instance" step in first-time setup instructions.

## Cross-cutting / regression

- [ ] Full existing backend test suite passes with `AUTH_ENABLED=true` (default-safe path).
- [ ] Manual smoke test: fresh clone, `docker-compose up`, confirm `AUTH_ENABLED` defaults to `false` out of the box (per design), homescreen shows correct status.
- [ ] Manual smoke test: add an asset while `AUTH_ENABLED=false`, then set `AUTH_ENABLED=true` + run `reset-admin-password`, restart, log in — confirm the asset added while disabled is visible under the new credentials (validates the core "data survives the transition" guarantee from the original discussion).
- [ ] `docs/architecture/AUTH.md` / ADR update reflects the shipped model (not just remediation intent).

## Manual validation required

Items above marked with browser/manual smoke-test language cannot be fully automated and require the founder (or QA lens) to click through in a real running instance before final `/approve`. Automated/grep/test-suite items can be verified by CI or by the `qa` review pass if this workflow is later routed through implementation.

## Next step

This validation stage has no implementation to validate against yet — approving it signals the acceptance criteria are correct and sufficient, not that they've been executed. Actual implementation should proceed via `/feature` (or continued engineering work) using `remediation.md` as the task list and this file as the Definition of Done. Once implemented, re-run this checklist for real before shipping.
