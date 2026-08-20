# Security Request: auth-toggle

## Summary

Introduce an `AUTH_ENABLED` environment flag (default `false`) that lets WealthSignal run without login for local/single-user self-hosting, while providing a clean, safe path back to authenticated mode without losing data. Pair it with a `make reset-admin-password` script as the single mechanism for setting/changing admin credentials, replacing the current env-var-only bootstrap.

## Background / how we got here

WealthSignal is single-user (one bootstrapped admin, no signup route — ADR 0005). The founder considered disabling login entirely to reduce local friction, on the mistaken assumption that "login" meant dealing with Google OAuth complexity. Discussion (`/discuss`, 2026-08-18 and 2026-08-20) established:

- There is no OAuth in the current system at all (Supabase/OAuth design was fully replaced by ADR 0005's self-issued bcrypt/HS256 email+password). Decision: do not add Google OAuth — self-hosted deployments can't reasonably share a shared OAuth client, and comparable self-hosted OSS (Grafana, Plausible, Nextcloud) defaults to local admin auth.
- Decision: do not build email-based password reset (SMTP/token surface, breaks "zero-setup self-host over plain HTTP"). Instead, a local `make reset-admin-password` script that updates the existing admin row directly.
- Decision: `AUTH_ENABLED` toggle, defaulting to **disabled**, is the desired UX for local/first-run convenience. This is a deliberate reversal of "secure by default" — the risk needs to be assessed and mitigated, not waved away.

## Verified current behavior (read from code, not assumed)

- `bootstrap_admin_user()` (`backend/app/api/auth.py:33-52`), called from `lifespan()` in `backend/app/main.py:33`, is an *existence guard*: it creates exactly one `User` row with a fresh `uuid.uuid4()` id **only if the `users` table is completely empty**, using `ADMIN_EMAIL`/`ADMIN_PASSWORD` from settings at that instant. On every subsequent startup it is a **permanent no-op** — changing the env vars later has zero effect on the stored row. This is documented in the function's own docstring as a deliberate anti-footgun (a restart must not be mistakable for a password reset).
- Every user-scoped endpoint (assets, transactions, snapshots, valuations, performance, xirr, export, import, dashboard, account, insights) depends on `get_current_user_id` (`backend/app/core/auth.py:45-57`), which raises `401` if the `access_token` cookie is missing/invalid. `get_session` (`backend/app/api/deps.py:9-21`) stamps `request.state.user_id` from the JWT `sub` claim; row-level security was removed post-migration (architecture-002) so **every query filters by `user_id` at the application layer instead of the database layer**. There is currently no bypass path, no `AUTH_ENABLED`-style flag, and no signup/second-user creation route anywhere in the codebase.
- Because `bootstrap_admin_user()` runs unconditionally in `lifespan()` regardless of any future auth-enabled state, the single admin `user_id` will already exist from the very first boot even while auth enforcement is off. This is the basis for the "no data loss on enable" design goal below — but it is a *design requirement to preserve*, not an automatic guarantee, since we are about to add a bypass path that must be built to honor it.

## Proposed design (from `/discuss`, not yet implemented)

1. **`AUTH_ENABLED` env flag, default `false`.** When `false`, requests skip the credential/JWT check entirely, but `request.state.user_id` (or equivalent) must still be resolved to the one existing bootstrapped admin user — never null, never an anonymous mode, never a second/different user. This preserves the app-layer "filter every query by user_id" invariant that replaced RLS.
2. **In-app toggle lives on the homescreen, but only reachable when authenticated.** (Revised from the original ask of an always-reachable homescreen toggle, based on the risk that a control which can disable the only access gate must not itself be reachable pre-authentication — otherwise it's a tamper/persistence vector.) Exact placement/reachability rules are for this workflow to pin down.
3. **Danger signaling when auth is disabled on a non-localhost deployment.** Preferred mechanism: an explicit env var set by the deployer at setup time (e.g., `DEPLOYMENT=local|hosted`), not runtime request-origin heuristics — Host-header/client-IP detection is unreliable behind Tailscale or a reverse proxy (this repo's own infra is heading toward Tailscale per ROADMAP), and a missed detection means the warning silently fails to fire exactly when it matters most.
4. **`make reset-admin-password`** becomes the *sole* mechanism for setting or changing admin email/password after first boot. `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars only ever take effect on the very first startup when the `users` table is empty (existing, unchanged behavior) — they are not a channel for changing credentials later, and this workflow should not add env-file re-read logic to `bootstrap_admin_user()` to avoid weakening its documented anti-footgun contract.

## Affected components

- `backend/app/api/auth.py` (`bootstrap_admin_user`, login endpoint)
- `backend/app/core/auth.py` (`get_current_user_id`)
- `backend/app/api/deps.py` (`get_session`, `request.state.user_id` stamping)
- All user-scoped API routers (assets, transactions, snapshots, valuations, performance, xirr, export, import, dashboard, account, insights) — every one currently assumes `get_current_user_id` always raises on missing auth; this assumption changes under `AUTH_ENABLED=false`.
- `Makefile` (new `reset-admin-password` target)
- Frontend: homescreen/settings surface for the in-app toggle, and the danger-state banner/notification.
- `docs/architecture/AUTH.md`, ADR 0005 (may need a superseding/amending ADR given this changes the security model established there).

## Threat surface to assess

- Exposure window: any request reaching a deployed instance with `AUTH_ENABLED=false` gets full read/write access to real portfolio data with no password gate. This is the core risk being traded for local convenience.
- Homescreen toggle as a tamper/persistence vector if reachable pre-auth (see design point 2 — needs explicit resolution in the assessment).
- Reliability of the "hosted/dangerous" signal — false negatives (silently no warning) are worse than false positives (alert fatigue), especially under reverse proxies / Tailscale.
- Data-continuity guarantee across disable→enable transitions (verified safe *if* built correctly per the bootstrap behavior above — assessment should confirm the bypass implementation actually honors this).
- `reset-admin-password` script itself: needs its own access control (must only be runnable by whoever has shell/server access, not exposed via any API), and must invalidate any existing sessions/JWTs issued under the old credentials.

## Known exploits or incidents

None yet — this is a pre-implementation security workflow, not an incident response. No prior CVE or breach related to this surface.

## Governance

This is an Authentication/Security model change and requires CEO approval per CLAUDE.md before implementation begins. This request captures decisions already discussed and tentatively agreed via `/discuss` on 2026-08-18 and 2026-08-20; formal approval happens through this workflow's stage gates, not the prior discussion.
