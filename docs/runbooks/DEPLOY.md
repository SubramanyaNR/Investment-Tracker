# Runbook — production deploy (VPS)

> Status: **live**. WealthSignal runs self-hosted on a single VPS (`167.233.141.50`) as an
> open-source, single-user app (MIT license, `architecture-002`) — not the paid multi-tenant SaaS
> this doc originally described. There is no Supabase, no OAuth, no signup flow, no RLS, no
> per-user billing. Deploying/redeploying infra changes is still a **gated** action — get CEO
> approval first per `CLAUDE.md`.

## Prerequisites
- VPS provisioned, Docker + Docker Compose installed (Postgres runs in Docker; backend/frontend
  run as systemd units — see `PROCESS-SUPERVISION.md`).
- ufw firewall active (see `FIREWALL.md`).
- Secrets present in `backend/.env` (never committed): `DATABASE_URL`, `ADMIN_DATABASE_URL`,
  `JWT_SECRET`, `ADMIN_EMAIL`/`ADMIN_PASSWORD` (first-run bootstrap only), `GEMINI_API_KEY`,
  `COOKIE_SECURE` (default `false` — see below).

## One-time database provisioning (before pointing the app at it)
The `app_user` role is **cluster-level** (holds a password) and is **not** created by migrations.
Run once as admin:
```sql
CREATE ROLE app_user LOGIN PASSWORD '<strong-password>' NOINHERIT;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
```
`app_user` is still least-privilege (no superuser, no table ownership) — but it no longer has an
RLS backstop behind it (removed in ADR 0005). Correct `WHERE user_id` filtering in application
code is the sole enforcement mechanism now.

## Deploy steps
1. Set both DSNs: `DATABASE_URL` (app_user) and `ADMIN_DATABASE_URL` (postgres/admin role).
2. `alembic upgrade head` (uses the **admin** role — a fresh DB has no schema; there is no
   `create_all`).
3. Build + start the stack (`make restart`, wraps `systemctl` — see `PROCESS-SUPERVISION.md`).
4. First boot bootstraps the single admin user from `ADMIN_EMAIL`/`ADMIN_PASSWORD` (idempotent —
   guarded on "any user exists", not a specific email). No signup flow exists.
5. Run `make validate`; smoke-test login + dashboard.

## Authentication (ADR 0005 — replaces the old Supabase section)

Self-issued bcrypt/HS256 auth, httpOnly cookies, CSRF via double-submit cookie, server-tracked
revocable refresh tokens rotated on every use. No email confirmation, no OAuth, no third-party
auth provider. Password reset is **admin-only**: edit `.env`/DB directly and restart — see
`ADMIN-ACCOUNT-RECOVERY.md`. Full design: ADR 0005, `AUTH.md`.

### `COOKIE_SECURE` — accepted trade-off, not an oversight
Defaults to `false` so login works over plain HTTP out of the box (zero-setup self-host
`docker-compose up`). This means session cookies travel unencrypted over
`http://167.233.141.50:3000` today — a conscious, founder-accepted trade (O5 decision), not a
gap. Set `COOKIE_SECURE=true` once serving behind real HTTPS (e.g. a Tailscale URL or a domain +
reverse proxy).

## Still open (from `docs/product/ROADMAP.md` tech debt)
- Automated offsite backups (`BACKUP-RESTORE.md` covers local `make backup`; offsite/rclone still
  todo).
- SSH (`22/tcp`) has no rate-limiting/fail2ban companion (`FIREWALL.md`).
- No CI/CD.

## Roadmap (not yet built)
GitHub Actions CI/CD, UptimeRobot monitoring, Ansible provisioning, PWA + Play Store (TWA). See
`../product/ROADMAP.md`.
