---
name: security-audit-and-hardening-backlog
description: Auth/multi-tenancy security audit lives in docs/SECURITY_AUDIT.md; pending hardening before paying customers
metadata: 
  node_type: memory
  type: project
  originSessionId: 5c99eb8c-d420-4afa-8154-7244b63e2bd5
---

A hostile security audit of the Supabase auth + multi-tenancy feature was done on 2026-06-03; full report is in `docs/SECURITY_AUDIT.md` (living doc — update finding statuses there).

Core authN/authZ/tenant-isolation verified correct by execution (no Critical/High). Fixed: PKCE flow (M3), user-scoped queries (L1), generic auth errors (L5), **RLS backstop (M1)**, child↔asset FK (L2), account-deletion endpoint (L4).

**M1 architecture (done 2026-06-03):** request path connects as non-superuser `app_user` (`DATABASE_URL`); `ADMIN_DATABASE_URL` (postgres) is used by migrations + the scheduler. All 8 tables have RLS `tenant_isolation` policy on the `app.current_user_id` GUC, set per-transaction LOCAL via an `after_begin` hook reading `session.info["user_id"]` (app/db/session.py). `app_user` role is cluster-level (password in .env) — NOT in migrations; fresh-deploy steps in `docs/SECURITY_AUDIT.md` §11. Never give app_user BYPASSRLS/ownership.

**Still required before paying customers:**
- M2: no rate limiting; unknown-`kid` tokens force a 1:1 outbound JWKS fetch (DoS amplification); `/market/*` is public + uncached.
- M4: stateless JWT, no revocation — short token TTL + email confirmation are Supabase **dashboard** settings (deferred).
- Automated test suite: the hardening above was verified by one-off scripts, not committed tests.
- L3: set CORS_ORIGINS / Supabase URLs to the real domain at VPS time.

**How to apply:** consult `docs/SECURITY_AUDIT.md` §8/§11 before go-live; re-run the §7 validation matrices after any auth/query/model change. Related: [[no-db-backups-exist]], [[vps-deploy-todo-automated-offsite-backups]], [[google-oauth-deferred-until-vps]].
