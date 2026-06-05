# Security Audit — Authentication & Multi-Tenancy

**Date:** 2026-06-03
**Scope:** Supabase auth + per-user data scoping (commits `a3c0552`, `b512e64` on `feature/supabase-auth`)
**Reviewer perspective:** Staff Security Engineer / Principal Backend / SaaS Production Readiness
**Method:** code review + executed tests (JWT forgery matrix, endpoint enforcement via TestClient, two-user isolation with transaction rollback, PyJWT/supabase-js library internals).

> Living document. Update the **Remediation backlog** statuses as fixes land. Re-run the
> validation matrices (Section 7) after any change to auth, queries, or the data model.

---

## 1. Executive summary

Core authN/authZ is **sound and proven by execution**: algorithm is pinned, signature/issuer/
audience/expiry are enforced, forged tokens are rejected, and tenant isolation is consistent across
all eight tables with no IDOR and no client-supplied identity. **No Critical or High exploitable
tenant-isolation bug was found.**

Gaps are **defense-in-depth / abuse-resistance**, not correctness: superuser DB role with no RLS
backstop, no rate limiting (incl. a JWKS-fetch amplification vector), OAuth `implicit` flow (tokens
in URL), and no token revocation.

| | Score | 
|---|---|
| Security | 7/10 |
| Production readiness | 6/10 |

**Verdict:** Conditionally approvable for paying users — the isolation logic itself is correct and
verified; complete the **Required** backlog first because a single future query mistake currently
has no second line of defense.

---

## 2. Architecture

- **AuthN:** `backend/app/core/auth.py` → `get_current_user_id`, a **sync** `Depends` (runs in
  threadpool, so its blocking JWKS fetch does not stall the event loop). Verifies Supabase JWT via
  `PyJWKClient` against the project JWKS, **ES256**.
- **Identity source:** the `sub` claim only. No Pydantic model exposes `user_id` — clients cannot
  inject identity.
- **AuthZ:** per-row `user_id` (NOT NULL) on all 8 tables; every query carries `WHERE user_id == sub`
  (first line) plus an RLS backstop (see below).
- **RLS status (2026-06-03 cutover):** request path connects as non-superuser **`app_user`** (no
  BYPASSRLS) via `DATABASE_URL`; all 8 tables enforce a `tenant_isolation` policy keyed on the
  `app.current_user_id` GUC, set per transaction (LOCAL, re-asserted on each BEGIN via an
  `after_begin` hook reading `session.info["user_id"]`) — survives mid-request commits, cannot leak
  across pooled connections, fail-closed (no GUC → 0 rows). Migrations + the scheduler use a separate
  **admin** (`postgres`/BYPASSRLS) connection via `ADMIN_DATABASE_URL`.
- **Public surface (intentional):** `/health`, `/market/*` (CoinGecko / MFAPI proxies).
- **Frontend:** `@supabase/supabase-js` (auth-js 2.107); Bearer token attached to every API call in
  `lib/api.ts`; `AuthProvider` gate; same-origin `/api` proxy (so backend CORS is effectively unused).

---

## 3. Authentication assessment — STRONG (evidence-backed)

Executed forgery / claim matrix — all rejected correctly:

| Attack | Result |
|---|---|
| Valid token | accepted, returns `sub` |
| Expired | 401 |
| Wrong audience / wrong issuer | 401 |
| Missing `sub` / missing `exp` | 401 (`require` enforced) |
| Non-UUID `sub` | 401 |
| `alg=none` | 401 (alg not allowed) |
| `alg=HS256` key-confusion | 401 (alg not allowed) |
| Tampered payload | 401 |
| Forged, unknown `kid` (live JWKS) | 401 (no matching key) |
| Forged, **real `kid`** + attacker signature (live JWKS) | 401 (signature verification failed) |
| Missing / malformed `Authorization` header | 401 |

- Algorithm pinned to `["ES256"]`; no downgrade.
- `PyJWKClientError ⊂ PyJWTError` → JWKS failures become 401, not 500.
- Key rotation handled (refresh-on-unknown-kid; cache only updated on successful fetch, so a transient
  Supabase outage will not wipe cached keys).

---

## 4. Authorization assessment — STRONG (evidence-backed)

All 15 endpoints tested with no token → **401**; public endpoints stay 200.

- Identity from JWT only; client cannot supply `user_id`.
- IDOR blocked: `delete_asset`, `sell-crypto`, `redeem-mf`, `top-up` filter the target by `user_id`
  → cross-user target returns 404.
- Merge trap (`POST /assets` get-or-create by `scheme_code`/`coingecko_id`) scoped per user.

---

## 5. Multi-tenancy assessment — STRONG (evidence-backed)

Two-user seed (rolled back, 0 rows persisted) — every path isolated:

```
[PASS] A/B dashboards see only own totals
[PASS] A asset list excludes B
[PASS] A cannot target B's asset by id (delete -> 404)
[PASS] A cannot sell B's crypto holding (-> 404)
[PASS] A transactions / valuations exclude B
```

Scheduler also scopes per user (distinct `Asset.user_id`; SIP transactions stamped from
`holding.user_id`).

---

## 6. Findings & remediation backlog

Status legend: `OPEN` · `FIXED` · `NEEDS-OPS` (requires infra/dashboard action).

### Critical
None.

### High
None confirmed.

### Medium
| ID | Finding | Status |
|---|---|---|
| M1 | **No RLS / superuser DB role.** Any future missing `WHERE user_id` = full-tenant breach with no backstop. Add least-privileged role + RLS keyed on JWT `sub`. | FIXED (2026-06-03) — `app_user` role + RLS policies + per-request GUC; verified fail-closed & no cross-tenant leak. See §11. |
| M2 | **No rate limiting + JWKS amplification (DoS).** Each unknown-`kid` token forces one outbound JWKS fetch (30s timeout, threadpool thread). Public uncached `/market/*` lets anon traffic burn upstream rate limits. | FIXED (2026-06-05, A5; 2026-06-05, A9) — `/market/*` cached + per-user rate limits + per-IP (per-client once nginx forwards XFF in B1; the Next proxy sends none). Unknown-`kid` JWKS negative cache added (A9): confirmed-bad kids cached for 60s, connection failures excluded. See ADR 0004. |
| M3 | **OAuth `implicit` flow (token in URL).** supabase-js defaults to implicit → access/refresh tokens in URL fragment (history/referrer exposure). Set `flowType: 'pkce'`. | FIXED (2026-06-03) |
| M4 | **No token revocation.** Stateless verify → deleted/banned user keeps access until `exp`. Mitigate with short token lifetime. | ACCEPTED-LIMITATION (Free plan) — session time-boxing + inactivity timeout are Supabase **Pro-only**; on Free we accept the default token lifetime (backend enforces `exp`, client auto-refreshes). No custom session-management code (deliberate). Revisit on Pro. See `DEPLOY.md` "Session controls (M4)". |

### Low
| ID | Finding | Status |
|---|---|---|
| L1 | `top_up_savings` FI-holding lookup and valuation `delete` not user-scoped (safe today via preceding ownership gate). | FIXED (2026-06-03) |
| L2 | No DB constraint that a child row's `user_id` matches its asset's `user_id`. | FIXED (2026-06-03) — composite FK `(asset_id,user_id)`→`assets(id,user_id)` on child tables. |
| L3 | `CORS_ORIGINS` not the real VM origin (moot due to same-origin proxy). | OPEN (revisit at VPS domain) |
| L4 | `ai_insights` / `portfolio_snapshots` don't cascade from `assets`; no account-deletion path → orphaned per-user rows. | FIXED (2026-06-03) — `DELETE /account` purges all caller rows (auth-user deletion still needs admin API). |
| L5 | Auth error responses echoed library detail. | FIXED (2026-06-03) |
| L6 | Snapshot upsert and asset merge not atomic; concurrent requests can race the unique constraint. | OPEN |

### Pre-existing (not introduced by this work, relevant to go-live)
No backups; no automated tests in repo; unpaginated `GET /transactions`.

---

## 7. Validation matrices (re-run after auth/query/model changes)

These were executed during the audit and should be turned into an automated suite.

**Auth:** valid / expired / wrong-aud / wrong-iss / missing-sub / missing-exp / non-uuid-sub /
alg=none / alg=HS256 / tampered / unknown-kid (live) / real-kid+forged-sig (live) / missing+malformed
header.

**Authorization:** every endpoint 401 without token; cross-user delete/sell/redeem/top-up → 404.

**Multi-tenancy:** two-user seed (rollback) — dashboards, asset list, transactions, valuations all
filter by owner.

**Abuse (TODO):** rate-limit behavior, oversized payloads, repeated unknown-kid tokens.

---

## 8. Required before production

1. **M1** — least-privileged DB role + Postgres RLS backstop. *(done — see §11)*
2. **M2** — rate limiting (per-IP/per-user) + cache `/market/*` + JWKS unknown-`kid` negative cache. *(done — A5, A9; ADR 0004. Per-IP becomes per-client once nginx forwards the client IP.)*
3. **M3** — PKCE flow. *(done)*
4. Set real `NEXT_PUBLIC_SUPABASE_ANON_KEY` *(done)*; require email confirmation; correct Supabase Site/Redirect URLs at VPS. *(A6 — checklist in `DEPLOY.md` "Supabase production configuration"; email confirmation enabled now, Site/Redirect/CORS at cutover. Short session controls are Pro-only — accepted Free-plan limitation, see M4.)*

## 9. Recommended
5. **M4** short token lifetime + documented revocation expectations.
6. **L1/L2** user-scope remaining queries *(done)* + child↔asset `user_id` consistency constraint *(done)*.
7. Automated test suite covering the Section 7 matrices. *(still recommended — fixes above were verified by one-off scripts, not committed tests)*
8. Account-deletion path *(done, L4)*; fix CORS origin at VPS (**L3**).

## 10. Nice-to-have
9. Generic error messages *(done, L5)*; atomic upserts via `ON CONFLICT` (**L6**); structured auth logging/alerting.

## 11. RLS deploy/ops notes

The `app_user` role is **cluster-level** (holds a password) so it is **not** created by migrations.
On a fresh database, provision it once before pointing the app at it:

```sql
CREATE ROLE app_user LOGIN PASSWORD '<strong-password>' NOINHERIT;
-- grants are (re)applied idempotently by migration 6a8bdc1bb742, but for a brand-new
-- DB you can also grant directly:
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
```

Then set both env vars: `DATABASE_URL` (app_user, pooler username `app_user.<ref>`) and
`ADMIN_DATABASE_URL` (postgres). Run `alembic upgrade head` (uses the admin role).
**Never** give `app_user` `BYPASSRLS` or table ownership. Migrations + the scheduler must keep
using the admin connection. Verify after deploy: as `app_user` with no `app.current_user_id` set,
`SELECT * FROM assets` returns 0 rows.
