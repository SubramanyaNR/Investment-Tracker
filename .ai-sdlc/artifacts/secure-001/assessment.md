# Security Assessment: auth-toggle

Workflow: secure-001 | Stage: assessment

## 1. Scope

Assess the risk of introducing an `AUTH_ENABLED` flag (default `false`), an authenticated-only in-app toggle, a deployment-danger banner, and `make reset-admin-password` as sole credential-change mechanism, against WealthSignal's current single-user, app-layer-authorization model (ADR 0005 — RLS removed, every query filtered by `user_id` derived from JWT `sub`).

## 2. Threat Model

### 2.1 Authentication

**T1 — Full data exposure while disabled.** With `AUTH_ENABLED=false`, any network-reachable client gets unauthenticated read/write to all portfolio data (net worth, holdings, transactions, XIRR/performance). This is not a bug to fix — it's the accepted tradeoff of the feature — but it means the feature's entire safety case rests on the deployer either (a) genuinely running localhost-only, or (b) being correctly warned when they're not. Severity: **Critical** if deployer expectation and reality diverge (e.g., this exact VM's own history — a box that started as "dev" and became the production VPS without anyone updating security posture).

**T2 — Bypass path incorrectly implemented.** The bypass replacing `get_current_user_id`'s 401 must resolve to the *one* existing bootstrapped user_id, never `None`/anonymous. If any endpoint is missed, or the bypass resolves user_id from an attacker-controllable source (e.g., a header, a query param) rather than a trusted server-side lookup, this becomes an authorization bypass even when `AUTH_ENABLED=true` in a misconfigured deployment, or an IDOR-equivalent if user_id is ever attacker-suppliable. Severity: **Critical**. Mitigation must be structural: single choke point (e.g., in `get_session`/`get_current_user_id` itself, not per-router), fetched from DB (`SELECT id FROM users LIMIT 1`), never trusted from the request.

**T3 — Homescreen toggle as privilege/persistence vector.** If the enable/disable control is reachable pre-authentication, an attacker who reaches a disabled instance during the exposure window (T1) could flip it, and — more importantly — a legitimate user who re-enables auth could have it silently flipped back off by anyone who still has access. Design already revised in `request.md` to require the toggle be authenticated-only; assessment confirms this is necessary, not optional. Severity: **High** if not enforced; mitigated by design if enforced.

**T4 — `reset-admin-password` script exposure.** If this logic is ever reachable via an API route (not just `make` CLI on the server), it becomes a remote credential-reset primitive with no verification step. Must be filesystem/CLI-only, requiring server (SSH/console) access — equivalent trust level to editing `.env` today. Severity: **Critical** if exposed via HTTP; **N/A** if kept CLI-only as scoped.

**T5 — Session invalidation on credential reset.** If `reset-admin-password` changes the password but existing JWTs remain valid (no session/token versioning), a previously-issued token continues to work post-reset — defeating the purpose of a reset (e.g., "someone else may have my password, I'm rotating it"). Severity: **Medium-High**. Needs either short JWT expiry already in place (verify) or a token-versioning/invalidation mechanism added as part of this change.

**T6 — First-boot credential weakness.** `bootstrap_admin_user()` seeds the permanent admin row from `ADMIN_EMAIL`/`ADMIN_PASSWORD` at first boot; if a self-hoster leaves defaults/placeholders in `docker-compose`/`.env.example` and never runs `reset-admin-password`, the "permanent no-op" property (a documented anti-footgun) becomes a footgun in the other direction — default creds persist forever with no forced-change nudge. Not new to this workflow, but the danger banner (design point 3) and onboarding docs should explicitly close this gap while we're touching this surface. Severity: **Medium**.

### 2.2 Multi-tenancy / Data Isolation

System is single-user by design (ADR 0005, no signup route) — classic multi-tenant cross-user leakage (IDOR across user_ids) is structurally out of scope *today*. However, T2's bypass path is the one place a second implicit "tenant" (anonymous/no-user) could be introduced if built wrong. Assessment finding: **the isolation model is sound only as long as "exactly one user_id, always" remains an invariant enforced at a single choke point** — this workflow must not let that invariant leak into per-endpoint logic.

### 2.3 API Surface

All listed routers (assets, transactions, snapshots, valuations, performance, xirr, export, import, dashboard, account, insights) currently assume `get_current_user_id` always either returns a valid id or raises. Under `AUTH_ENABLED=false` this assumption changes for the whole surface at once — favors implementing the bypass **inside** `get_current_user_id`/`get_session` (single choke point) over duplicating "if not AUTH_ENABLED, skip" checks per router, which would be both a change-discipline violation (touches N files unnecessarily) and a much larger attack surface for T2-style mistakes.

### 2.4 Data Exposure

No new data fields or endpoints are proposed. Exposure risk is entirely about *who* can reach existing endpoints (T1), not new data being surfaced. `reset-admin-password` must not log or echo the new plaintext password to shell history/logs by default — prompt interactively or read from a file, not a bare CLI arg.

### 2.5 OWASP-relevant risks

- **A01 Broken Access Control** — T1, T2, T3 all map here; this is the dominant risk category for this workflow.
- **A02 Cryptographic Failures** — not touched (bcrypt/HS256 unchanged), but T5 (session invalidation) borders this if JWT expiry is long-lived.
- **A05 Security Misconfiguration** — T1 and T6 are fundamentally misconfiguration risks (feature ships "off-safe" only if the deployer engages with the danger banner correctly).
- **A07 Identification and Authentication Failures** — the entire feature is a deliberate, scoped weakening of this category; must be bounded exactly as designed (single fixed user, no anonymous multi-user drift).

## 3. Findings Summary

| ID | Risk | Severity | Status |
|----|------|----------|--------|
| T1 | Full unauthenticated data access while disabled | Critical | Accepted tradeoff; mitigated by default-off + danger banner design |
| T2 | Bypass resolves user_id incorrectly / attacker-controllable | Critical | Must fix via single-choke-point design |
| T3 | Pre-auth-reachable toggle = tamper/persistence vector | High | Mitigated by design (authenticated-only toggle) — must be enforced in remediation |
| T4 | reset-admin-password exposed via HTTP | Critical | Must remain CLI-only |
| T5 | No session invalidation on password reset | Medium-High | Needs explicit handling |
| T6 | Default/placeholder first-boot credentials never rotated | Medium | Address via banner + docs |

## 4. Recommendation

Proceed to `remediation`, prioritizing: (1) single-choke-point bypass implementation (closes T2, simplifies T3 enforcement), (2) CLI-only `reset-admin-password` with session invalidation (closes T4, T5), (3) explicit `DEPLOYMENT=local|hosted` env var over request-origin heuristics for the danger banner (closes reliability concern from `request.md`), (4) authenticated-gating of the homescreen toggle (closes T3), (5) onboarding docs nudging credential rotation (addresses T6).

No blocking objections to proceeding — risks are known, bounded, and each has a concrete mitigation path. Recommend explicit CEO sign-off on **accepting T1 as a permanent, by-design tradeoff** (not something remediation can eliminate — only bound and warn about), since that's a product-risk decision, not just an engineering one.
