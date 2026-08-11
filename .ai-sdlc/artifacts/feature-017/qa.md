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
- **Real browser session** (audit: "the part most likely to surface as a real bug... recommend
  closing this specific gap before calling the feature done") — closed using the project's
  `e2e-ui-test` skill (real headless Chromium, production build, not curl): **Sign in**, **Dashboard
  loads (KPIs)**, **Theme toggle**, **Asset-type switching** all PASS. Confirms the session cookie
  is set by a real browser, sent back correctly on a subsequent protected fetch (dashboard), and the
  UI mounts/interacts correctly post-login (no leftover Supabase-import breakage). Run stopped at
  the mutual-fund search step on a `502 Bad Gateway` from `api.mfapi.in` — confirmed via direct
  `curl` to be a pre-existing, already-documented VM egress issue unrelated to this cutover
  (`mfapi-unreachable-from-this-vm` in project memory; CoinGecko reachable fine from the same host).
  Not pursued further — chasing an unrelated external connectivity issue is out of this task's scope.
  A full CSRF-protected mutation via literal browser click-through (not just curl) was not reached
  because of this external block; the curl-based CSRF checks (#7–9 above) plus the browser reaching
  and correctly rendering an authenticated, interactive page are the coverage achieved.
- **Compose project-name collision** — third compose file (`docker-compose.yml`) checked; defines
  no Postgres service so can't collide by service name, but given the explicit `-p` guidance for
  consistency anyway since it's not impossible to misuse.

### Verdict
**Pass.** 211 automated tests, 15 live adversarial checks, all green. Two real bugs were caught and
fixed during this work (not pre-existing, both introduced by the schema change and caught before
reaching production): `manual_holdings` RLS omission (integration tests), `_complete_onboarding`'s
NOT-NULL violation on upsert-insert (integration tests). Neither would have been caught by code
inspection alone.
