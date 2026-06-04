# Authentication & multi-tenancy design

> The WHY + shape of auth. For the evidence-backed audit, open findings, and ops/RLS provisioning,
> see `../runbooks/SECURITY-AUDIT.md` (living doc). For per-decision rationale see
> `decisions/0002-supabase-auth-es256.md` and `decisions/0003-rls-app_user-backstop.md`.

## Shape
- **Provider:** Supabase Auth (email/password now; Google OAuth deferred until a real domain/VPS).
- **Frontend:** `@supabase/supabase-js` with **PKCE** flow. `AuthProvider` gates the app;
  `lib/api.ts` attaches the Bearer token to every API call; requests go same-origin via the `/api`
  proxy (so backend CORS is effectively unused).
- **Backend AuthN:** `backend/app/core/auth.py` → `get_current_user_id`, a sync `Depends` (runs in
  threadpool so its blocking JWKS fetch doesn't stall the event loop). Verifies the Supabase JWT via
  `PyJWKClient` against the project JWKS, algorithm **pinned to ES256**.
- **Identity source:** the JWT `sub` claim **only**. No Pydantic model exposes `user_id` — clients
  cannot inject identity.

## Multi-tenancy (two lines of defense)
1. **App layer:** every user-owned table has a `user_id` (NOT NULL); every query carries
   `WHERE user_id == sub`.
2. **DB layer (RLS backstop):** the request path connects as non-superuser **`app_user`** (no
   BYPASSRLS). All 8 tables enforce a `tenant_isolation` policy keyed on the `app.current_user_id`
   GUC, set per transaction (LOCAL, re-asserted on each BEGIN). Fail-closed: no GUC → 0 rows.
   Migrations + the scheduler use a separate **admin** connection (`ADMIN_DATABASE_URL`, BYPASSRLS).

## Invariants (do not break)
- Never trust a client-provided `user_id`; derive it from the verified JWT.
- Ownership checks return 404 (not 403) for another user's resource — don't leak existence.
- `POST /assets` merge-by-`scheme_code`/`coingecko_id` is scoped per user.
- Public surface is intentional and minimal: `/health`, `/market/*`.
- Any new query on a user-owned table **must** filter by `user_id` even with RLS present — RLS is a
  backstop, not a license to skip the app-layer filter.

## Known open items (see audit for full backlog)
- **M2** — no rate limiting; `/market/*` uncached (JWKS-fetch amplification + upstream burn). OPEN.
- **M4** — no token revocation (stateless verify); mitigate with short token TTL. NEEDS-OPS.
- **L6** — snapshot upsert / asset merge not atomic; concurrent requests can race. OPEN.
