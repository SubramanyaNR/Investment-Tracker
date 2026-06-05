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

## Supabase production configuration (A6 checklist)

All in the **Supabase console** (no code) — most take effect only with the real domain, so apply
them at cutover. Email confirmation can be enabled **now** (the frontend already handles it).

| # | Setting | Where | When | Verify |
|---|---|---|---|---|
| 1 | **Enable "Confirm email"** | Authentication → Sign In / Providers → Email | **Now** (no domain needed) | See "Expected signup flow" below. |
| 2 | **Site URL** = `https://<domain>` | Authentication → URL Configuration | **Cutover (B1)** | OAuth/email links point at the real domain, not localhost. |
| 3 | **Redirect URLs** = `https://<domain>/*` | Authentication → URL Configuration | **Cutover (B1)** | Email-confirm / OAuth redirects land back on the app. |
| 4 | **`CORS_ORIGINS=https://<domain>`** in `backend/.env` | env (not Supabase) | **Cutover (B1)** | Set to the real origin (fixes audit **L3**). Moot under the same-origin `/api` proxy, but set correctly anyway. |

> These are **founder actions** — they cannot be scripted from the repo. Email confirmation needs a
> working mailer (Supabase's default for low volume, or SMTP). Google OAuth stays disabled until #2/#3
> are set on a real domain (see project memory `google-oauth-deferred-until-vps`).

### Expected signup flow (with "Confirm email" on)
1. User submits email + password on the sign-up screen.
2. Supabase creates the user **without a session** and sends a confirmation email.
3. The app shows *"Check your email to confirm your account, then sign in."* (`LoginScreen.tsx`) —
   the user is **not** logged in yet.
4. User clicks the confirmation link → email is verified.
5. Only then does sign-in succeed and a session is issued; protected APIs work.
   (Before confirmation, sign-in fails and the backend issues no valid token.)

### Session controls (M4) — accepted Free-plan limitation
Supabase **Free** does not offer **session time-boxing** or **inactivity timeout** (Pro-plan
features). We accept this for now: the access token has Supabase's default lifetime, the backend
enforces `exp`, and the client silently refreshes (`autoRefreshToken`). Shorter/forced session
controls can be enabled **if/when we move to Supabase Pro**. **No custom session-management code is
introduced** (deliberate — it would duplicate auth state and add risk). This is the residual M4 gap.

## Still required before paying users (from SECURITY-AUDIT §8)
- ~~**M2** rate limiting + cache `/market/*`~~ — **done (A5)**; per-IP becomes per-client once nginx
  forwards the real client IP (the Next proxy sends no `X-Forwarded-For`). JWKS unknown-`kid` negative
  cache still open. See ADR 0004.
- Email confirmation — enable now (A6 checklist above). Session time-boxing/inactivity timeout are a
  **Free-plan limitation** (accepted; Pro-only) — residual M4 gap, no custom code.
- Automated offsite backups (`BACKUP-RESTORE.md`) — roadmap **A7**.
- ~~A committed test suite for the §7 matrices~~ — **done (A3a/A3b)**.

## Roadmap (not yet built)
GitHub Actions CI/CD (push to `master` → deploy), UptimeRobot monitoring, Ansible provisioning,
PWA + Play Store (TWA). See `../product/ROADMAP.md`.
