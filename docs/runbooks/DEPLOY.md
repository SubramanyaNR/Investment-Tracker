# Runbook — production deploy (VPS)

> Status: **planned** (not yet deployed). Target: Hetzner CX21 (~$5/mo), Docker Compose, domain +
> Nginx + Certbot (HTTPS). Deploying is a **gated** action — get CEO approval first.

## Prerequisites
- VPS provisioned, Docker + Docker Compose installed.
- Domain pointed at the VPS; Nginx reverse proxy + Certbot TLS.
- Supabase project: Site URL + Redirect URLs set to the real domain; email confirmation on; short
  token TTL (mitigates M4 — no revocation).
- Secrets present in `backend/.env` (never committed): `DATABASE_URL`, `ADMIN_DATABASE_URL`,
  Supabase keys, `GEMINI_API_KEY`, `CORS_ORIGINS` = real origin (fixes audit L3).

## One-time database provisioning (before pointing the app at it)
The `app_user` role is **cluster-level** (holds a password) and is **not** created by migrations.
Run once as admin (full grants in SECURITY-AUDIT §11):
```sql
CREATE ROLE app_user LOGIN PASSWORD '<strong-password>' NOINHERIT;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
```
**Never** give `app_user` BYPASSRLS or table ownership.

## Deploy steps
1. Set both DSNs: `DATABASE_URL` (app_user, pooler username `app_user.<ref>`) and
   `ADMIN_DATABASE_URL` (postgres).
2. `alembic upgrade head` (uses the **admin** role — a fresh DB has no schema; there is no
   `create_all`).
3. Build + start the stack (Docker Compose).
4. **Verify RLS:** as `app_user` with no `app.current_user_id` set, `SELECT * FROM assets` returns
   0 rows.
5. Run `make validate`; smoke-test login + dashboard; re-run SECURITY-AUDIT §7 auth/tenancy matrices.

## Still required before paying users (from SECURITY-AUDIT §8)
- **M2** rate limiting + cache `/market/*`.
- Email confirmation + short token TTL.
- Automated offsite backups (`BACKUP-RESTORE.md`).
- A committed test suite for the §7 matrices.

## Roadmap (not yet built)
GitHub Actions CI/CD (push to `master` → deploy), UptimeRobot monitoring, Ansible provisioning,
PWA + Play Store (TWA). See `../product/ROADMAP.md`.
