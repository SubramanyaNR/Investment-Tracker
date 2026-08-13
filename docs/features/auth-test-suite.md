# Auth Test Suite — Automated Validation of Custom bcrypt/HS256 Auth

**Status:** ✅ Complete
**Last updated:** 2026-08-13
**Scope:** Automated test coverage for the custom bcrypt/HS256 auth cutover (ADR
[0005](../architecture/decisions/0005-custom-auth-single-user.md)), which replaced Supabase Auth
(ADR [0002](../architecture/decisions/0002-supabase-auth-es256.md)) as part of `architecture-002`.

## What was delivered

Automated test coverage for every completion condition the CEO decision log
(`.ai-sdlc/artifacts/architecture-002/planning.md`) required for the auth phase: login, token
expiry/refresh, revocation, bootstrap, and ownership checks.

### 1. Password hashing & JWT primitives (Unit)
**File:** `backend/tests/unit/test_auth.py`

- bcrypt hash/verify round trip, wrong password rejected, hash isn't the plaintext, malformed
  hash fails closed
- Access token: valid token returns `sub`, missing cookie / expired / missing `sub` / non-UUID
  `sub` / wrong secret / `alg=none` / tampered payload / malformed token → 401
- **Old Supabase-style ES256 token explicitly rejected** — confirms the JWKS/ES256 verification
  path is gone, not just unused
- Refresh token hashing: deterministic, hash isn't the raw value, expiry set in the future
- CSRF: GET requests and the login path are exempt, requests with no session are exempt, missing
  cookie / missing header / mismatched values rejected, matching values accepted

### 2. Auth endpoints, end-to-end (Integration)
**File:** `backend/tests/integration/test_auth_endpoints.py`

Tests the full HTTP flow through real endpoints:
- Bootstrap creates the single admin user and is idempotent (guarded on "any user exists")
- Login: correct credentials succeed, wrong password / unknown email rejected, repeated failures
  rate-limited
- `/me` requires a valid session
- Refresh issues new tokens and rotates the refresh token; rejected without the refresh cookie
- Logout revokes the refresh token
- CSRF enforced on mutating requests (missing/wrong header rejected); login itself is CSRF-exempt
- **Old-style Bearer token no longer accepted** — confirms cookie-based sessions fully replaced
  the prior client-held-token model

### 3. Multi-tenancy / ownership isolation (Integration)
**File:** `backend/tests/integration/test_auth_isolation.py`

Two-user isolation across the full API (app-layer `WHERE user_id = ...` filtering — the sole
enforcement mechanism now that RLS has been removed per ADR 0005):
- Dashboard, asset list, transactions, valuations, and snapshots each isolate by user
- Cross-user DELETE → 404 (existence not leaked, not 403)

### 4. Authorization matrix (Integration)
**File:** `backend/tests/integration/test_authorization.py`

- Every protected endpoint returns 401 without authentication
- Public endpoints (e.g. `/health`) remain accessible without a session

### 5. Rate limiting (Integration)
**File:** `backend/tests/integration/test_auth_ratelimit.py`

- Authenticated per-user rate limit enforced
- Anonymous per-IP rate limit enforced on public endpoints
- (Precise window/timing behavior is covered in unit tests with mocked clocks, not here — timing
  is fragile in CI)

## Test results

```
backend/tests/unit/test_auth.py + integration/{test_auth_endpoints,test_auth_isolation,test_authorization}.py
✅ 60 passed

Full backend suite (unit + integration)
✅ 211 passed
```

## How to run

```bash
# Auth-only
make test-int -k auth

# Specific suites
make test-int -k test_auth_endpoints
make test-int -k test_auth_isolation

# Full backend suite
make test-int
```

## Design decisions

### Integration vs. unit split
- **Unit** (`test_auth.py`): password hashing and JWT/CSRF logic in isolation.
- **Integration** (`test_auth_endpoints.py` etc.): full HTTP flow, so wiring bugs (middleware
  order, cookie attributes, route dependencies) are caught, not just parsing bugs.

### IDOR test strategy
Cross-user operations return **404, not 403**, to avoid leaking existence. Tests verify this is
enforced (`test_delete_other_users_asset_returns_404`).

### RLS removed — app-layer filtering is now the only backstop
ADR 0005 dropped all RLS tenant-isolation policies (single-user, self-hosted deployment — no
other tenant to leak to). `test_auth_isolation.py` therefore validates isolation purely at the
application layer; there is no database-level backstop left to fall back on if a `WHERE user_id`
filter is ever forgotten. Re-run this suite after any change that touches query filtering.

### Old auth paths are tested as explicitly rejected, not just absent
Both the ES256/JWKS token format and the Bearer-token transport from the pre-cutover (Supabase)
auth model have dedicated rejection tests, rather than relying on their absence from the codebase.

## Known limitations

- **Rate limiting timing:** exact window behavior (100 req/60s) is unit-tested with mocked clocks,
  not integration-tested — precise timing is fragile in CI.
- **Abuse matrix incomplete:** oversized payloads and repeated-failure amplification patterns are
  deferred to post-VPS-deploy, pending real traffic patterns to test against.
- **Password reset:** by design, there is no in-app reset flow (ADR 0005) — admin resets via
  `.env`/DB and restart, documented in a runbook, not covered by this test suite.

## References

- **ADR 0005** — the decision record this suite validates.
- **`.ai-sdlc/artifacts/architecture-002/planning.md`** — CEO decision log requiring this coverage
  as a completion condition for the auth phase.
- **AUTH.md** — authentication architecture these tests verify.
- **SECURITY-AUDIT.md** — broader security posture; the multi-tenancy/authorization matrices here
  originated from its validation matrices under the prior (Supabase) auth model and were carried
  forward.
