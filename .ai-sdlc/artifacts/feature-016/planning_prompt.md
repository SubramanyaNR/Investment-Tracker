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
# Feature Request: Automated Backups (Local-Only, No Offsite) — Daily

## User Request

"Automated backups (local-only) - daily backup". Continuation of this same workflow (`feature-016`,
`O1`) — resuming rather than duplicating; scope decisions below carry forward from earlier
planning, with one major factual update.

## Context has changed since this workflow was first planned — request rewritten accordingly

This request was originally written when the live app still ran against **Supabase**. Since then,
**`feature-017` shipped**: the live app now runs against a **local Postgres container**
(`investment_tracker_postgres`, `127.0.0.1:5433`, database `investment_tracker`), custom auth, no
Supabase dependency at all. This changes which backup mechanism is actually correct — not just
"which of two scripts to pick," as originally framed, but **both pre-existing scripts are now
broken against the current setup**, for different reasons:

1. **`make backup`** (`Makefile`) — runs `docker run --rm postgres:17 pg_dump "$DATABASE_URL?sslmode=require"`.
   Two problems now: (a) the local Postgres container has SSL **off**
   (confirmed: `SHOW ssl` → `off`) — `sslmode=require` will fail the connection outright; (b) an
   ephemeral `docker run` container's `localhost` doesn't resolve to the *host's* `localhost` —
   it needs to reach `investment_tracker_postgres` by container name on a shared Docker network,
   or connect via `host.docker.internal`, or (simplest) run `pg_dump` **inside** the target
   container directly via `docker exec`, avoiding a second throwaway container and the networking
   problem entirely.
2. **`backup.sh`** (repo root) — targets `docker-compose.yml`'s `postgres` service, which
   **doesn't exist** in that file (never did — that compose file only defines `backend`/
   `frontend`), with the wrong user (`investment_user` vs. actual `investment_admin`/`app_user`)
   and wrong database name (`investment_db` vs. actual `investment_tracker`). This script has
   likely never actually worked against anything real.

**Recommendation for planning to evaluate, not a decision already made**: `docker exec
investment_tracker_postgres pg_dump -U investment_admin investment_tracker | gzip > ...` — runs
inside the target container, sidesteps both the SSL and cross-container-networking problems, and
matches the pattern already used throughout `feature-017`'s own verification work this session.

## Resolved scope decisions (carried forward from earlier planning, still stand)

1. **Local-only, no offsite copy.** Founder's explicit choice, discussed and risk-flagged
   previously: a same-server backup doesn't survive a whole-VM/disk loss, but is simplest and
   needs no new dependencies (no rclone, no cloud account). This is now a **stronger** case for
   local backups mattering at all than before — pre-cutover, Supabase was a second copy of the
   data by construction; post-cutover, the local Postgres container is genuinely the *only* copy of
   anything, so even a same-disk backup is real, non-redundant protection against a much larger
   class of everyday mistakes (bad migration, accidental `DELETE`, app bug) than "nothing." Offsite
   remains a explicit, deferred, separate decision — not part of this task.
2. **Schedule**: daily, via cron.
3. **Retention**: existing scripts both defaulted to keeping the last 7. Storage sizing was
   discussed this session — the actual DB is ~8KB today (freshly cut over, no real holdings yet),
   and even years of realistic personal-portfolio-tracker usage (a handful of transactions/year,
   one snapshot/day) is expected to stay in the low single-digit MB range. **Retention could
   reasonably be longer than 7 days (e.g. 30) at negligible storage cost** — worth deciding
   explicitly in planning rather than defaulting to the old scripts' number by inertia.
4. **Restore test required**: at least one verified restore, against the disposable sandbox
   (`investment_tracker_selfhost_postgres`, `127.0.0.1:5432`) — never the live container. Per
   `BACKUP-RESTORE.md`: "a backup you've never restored is a hypothesis, not a backup."
5. **Failure visibility**: some way to notice a silently-failed scheduled backup (log file +
   lightweight check) — proportionate, no new notification infrastructure.

## What this touches

- A backup script (new, or a corrected `make backup`/`backup.sh` — planning's call which) targeting
  `investment_tracker_postgres` specifically, not the sandbox and not a stale Supabase reference.
- A cron entry.
- `docs/runbooks/BACKUP-RESTORE.md` — currently describes the old Supabase-targeted `make backup`
  flow; needs updating to match whatever this task actually builds (in scope for this task, since
  it's the direct operational documentation for what's being built here — not the broader stale-docs
  sweep already logged as separate tech debt in `ROADMAP.md`).

## What does NOT change

- No changes to schema, migrations, auth, or product features.
- No offsite/cloud backup (separate, deferred decision).
- Not bundled with O2 (firewall) or O3 (process supervision) — independent, any order.
- Does not touch the disposable sandbox container's own data — sandbox is a restore-test *target*,
  not a backup *source*.

## Constraints / governance

- Infrastructure change touching how the live instance's real data is protected — per `CLAUDE.md`,
  requires explicit CEO approval, same as O4 and `feature-017`. This request constitutes that
  approval for the scope described.
- No founder-only external prerequisite (no cloud account/OAuth) — fully completable end-to-end.
- Validate the change actually works: confirm a scheduled (not just manually-invoked) backup ran
  unattended, and confirm the restore test.

