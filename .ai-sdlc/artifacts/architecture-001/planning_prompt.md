# Planning Prompt

## Product Context
# Product Context - WealthSignal

WealthSignal is a personal multi-asset portfolio tracker for Indian retail investors. It provides unified portfolio observability (net worth, P&L, allocation) across crypto, mutual funds, and fixed income (FD/RD/PPF).

Key Principles:
- Portfolio observability is the primary goal.
- Not a trading or brokerage app.
- Focus on clarity and trust for the retail investor.


## Architecture Context
# Architecture Context

Stack:
- Backend: FastAPI (Python 3.11), SQLAlchemy 2.0 (async), Pydantic.
- Frontend: Next.js 16 (App Router), React 19, Tailwind 4.
- Database: Postgres 16 (UUID PKs, Numeric for money).
- Auth: Supabase Auth (PKCE flow).

Key Patterns:
- Same-origin /api proxy for backend access.
- All DB operations must be async.
- Identity derived only from verified JWT 'sub' claim.
- RLS enforced as a backstop; app-layer filtering is mandatory.


## Governance Context
# Governance Context

Operating Model:
- One system, seven lenses (PM, Investor Advisor, CTO, Architect, Eng Lead, QA, Security).
- Hard CEO approval gate at Step 6 of SDLC.
- Gated decisions: Architecture, Data Model, Auth, Security, Product Direction.
- Free lane: Docs, tests, copy polish within approved scope.


## Investor Experience Context
# Investor Experience Context

Investor Trust & Clarity:
- Metric comprehension: Are units and calculations clear?
- Dashboard clarity: Mobile-first status at a glance.
- Investor trust: Presentation must build confidence; limitations must be clear.
- Presentation of insights: Language must be investor-friendly, not overly technical.


## Request
# Architecture Request: Production VPS Cutover

## Change requested

This VM was just migrated to and confirmed by the founder (2026-07-30) as the **permanent
production server** for WealthSignal — not another throwaway dev box like its predecessor. It is
currently configured exactly like a dev VM. This request scopes the cutover to a real production
posture, matching roadmap milestones V2–V7 (`docs/product/ROADMAP.md`, `TASKS-BEFORE-VPS.md`):

1. **Domain + HTTPS** — Nginx reverse proxy + Certbot (Let's Encrypt) in front of the app.
2. **Supabase auth cutover** — Site URL, Redirect URLs, and `CORS_ORIGINS` pointed at the real
   domain instead of `localhost:3000`. Unlocks Google OAuth (already coded, just gated on this).
3. **Process supervision** — replace the current bare `nohup` backend/frontend processes (survive
   the shell session but not a reboot; no systemd units exist) with systemd units or the existing
   `docker-compose.yml` stack, so the app restarts automatically on boot/crash.
4. **CI/CD** — GitHub Actions: push to `master` → deploy. No `.github/workflows/` currently exists.
5. **Automated offsite backups** — cron `make backup` (pg_dump against Supabase) → rclone → Google
   Drive, plus a proven restore path. No backup has ever been taken on this VM; `backups/` doesn't
   exist.
6. **Uptime monitoring** — UptimeRobot (free tier) against the public health endpoint.

## Current state (verified by direct inspection, 2026-07-30)

- No `nginx`, no `certbot`, no domain configured anywhere (`CORS_ORIGINS=http://localhost:3000`)
- Backend/frontend run as bare `nohup` processes via `make dev`/`make restart` (PPID=1, not
  systemd-managed) — confirmed via `ps`/`systemctl`; a reboot would not bring the app back up
  since no systemd units or crontab exist
- `docker-compose.yml` exists in the repo but is not what's actually running here
- No `.github/workflows/` directory
- No `backups/` directory, no cron entries, no backup has ever run on this VM
- DB is Supabase-managed Postgres (not local) — confirmed via `backend/.env` `ADMIN_DATABASE_URL`
- This VM's real IP is `<vps-ip>` (memory/docs still reference the *previous* VM's IP,
  `172.23.80.6` — needs correcting regardless of this workflow's outcome)
- App itself is functional: frontend builds clean, backend healthy, core product features (asset
  mgmt, XIRR, CSV import, performance movers, onboarding, CSV export) already shipped to `master`

## Known adjacent issue (separate, not blocking this workflow)

`api.mfapi.in` (mutual fund NAV/search provider) is unreachable from this VM's network — TCP
connect to port 443 hangs even by direct IP, while general internet and CoinGecko work fine. This
looks like a network/security-group egress gap possibly related to this being a fresh VM. Worth
checking whether the same egress review that covers this cutover also resolves it, since it may be
the same root cause (outbound firewall/security-group rules on the new host).

## Constraints

- Single-user app currently, pre-revenue — cost-consciousness matters (Hetzner-class VPS budget,
  ~$5/mo, per `docs/product/VISION.md`)
- No downtime tolerance requirement yet (no paying users), but this is the first real production
  deploy, so correctness and rollback-ability matter more than speed
- DB is Supabase (not self-hosted) — this cutover is about the app/edge layer, not the database
- No automated test suite currently gates infra changes; validation will be manual
  (`make validate`, e2e-ui-test skill, manual smoke test) per `docs/runbooks/LOCAL-DEV.md`

## Governance concerns

This request touches **infrastructure, production deployment, and auth configuration (Supabase
Site URL/CORS/redirect)** simultaneously — all explicitly listed in `docs/CLAUDE.md` as requiring
CEO approval before implementation. It does not touch database schema, migrations, or the
authentication *model* itself (still Supabase JWT; only its configured URLs change). Recommend
sequencing as separable, individually-approvable phases (e.g. domain/SSL first, then Supabase
cutover, then CI/CD, then backups/monitoring) rather than one large all-or-nothing change, so each
phase can be validated before the next begins.

