# 0002 — Supabase Auth with ES256 JWT verification

- Status: **Superseded 2026-08-10** by custom bcrypt/HS256 auth — see
  `0005-custom-auth-single-user.md` and `architecture-002`/`feature-017`. The OSS self-host pivot
  (2026-07-30) dropped Supabase entirely; kept here for historical record.
- Date: 2026-06-04 (recorded; implemented on `feature/supabase-auth`)

## Context
Single-user app needed real auth + multi-tenancy before launch. Building auth in-house (password
hashing, email confirmation, OAuth, session management, key rotation) is high-risk and slow for a
solo founder. Identity must be unforgeable and never client-supplied.

## Decision
Use Supabase Auth (managed) for signup/login and token issuance. The backend verifies the Supabase
JWT itself via `PyJWKClient` against the project JWKS, with the algorithm **pinned to ES256**.
Identity is taken from the `sub` claim only; no Pydantic model exposes `user_id`. Frontend uses the
**PKCE** flow (not implicit) so tokens never land in the URL.

## Consequences
- Buys email/password + future OAuth + key rotation without owning that code (build-vs-buy: buy).
- Pinned ES256 blocks `alg=none` and HS256 key-confusion; forged/expired/wrong-aud tokens → 401
  (proven by the forgery matrix in `../../runbooks/SECURITY-AUDIT.md` §3).
- Stateless verification means **no revocation** until token expiry — mitigate with short TTL (M4).
- Couples auth to Supabase availability; JWKS failures degrade to 401, not 500.
