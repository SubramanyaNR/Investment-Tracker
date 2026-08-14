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
# Feature Request: Process Supervision (systemd units)

## User Request

"start O3 process supervision"

## Context

This is `O3` in `docs/product/FEATURE-BACKLOG.md` / step 3 in `docs/product/ROADMAP.md`'s
operational hardening sequence (Operational Hardening — Personal Instance, added 2026-08-06).

Background:
- This VM (`<vps-ip>`, Hetzner) is the founder's actual live personal instance of
  WealthSignal, not a build/reference box (`[[this-vm-is-the-production-vps]]`).
- Today, backend (`uvicorn`) and frontend (`next start`) are started via the project `Makefile`
  (`make backend`, `make frontend` / `make dev`) as bare `nohup` background processes:
  ```
  backend: nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 >/tmp/it-backend.log 2>&1 & echo $! >/tmp/it-backend.pid
  frontend: nohup npm start >/tmp/it-frontend.log 2>&1 & echo $! >/tmp/it-frontend.pid
  ```
  No auto-restart on crash, no auto-start on boot. Confirmed as a live gap 2026-08-13
  (`feature-018`): a host reboot during that session killed both processes and they stayed down
  until manually restarted — the app was fully unreachable until someone noticed.
- Postgres (`investment_tracker_postgres`) already restarts via Docker's own restart policy (or
  at minimum `docker start` on demand) — not in scope here, this request is specifically about
  the backend/frontend bare processes.
- Roadmap explicitly calls this out as step 3, right after the firewall (O2, done 2026-08-13,
  `feature-018`) and before Tailscale (O4, already done) in the operational-hardening sequence —
  this request follows that sequence.

## Goal

Backend and frontend both:
- Auto-start on host boot (after Docker/Postgres is up, and after `ufw` per O2 sequencing —
  network should already be locked down before the app starts accepting connections).
- Auto-restart on crash (a `Restart=on-failure` policy, not restart-storm-prone `Restart=always`
  with no backoff).
- Log to a location consistent with existing tooling (`/tmp/it-backend.log` /
  `/tmp/it-frontend.log` today via `Makefile`, or systemd's own journal — implementer's call,
  should be documented either way).
- Coexist with the existing `Makefile` targets (`make backend`, `make frontend`, `make dev`,
  `make restart`, `make stop`) used for local dev iteration — planning should address whether
  those targets should be repointed at `systemctl start/stop` or left as-is for manual/dev use
  with systemd as the boot-time/crash-recovery path specifically.

## Constraints / concerns to address in planning

- **Must not break the existing dev workflow.** `make dev` / `make restart` are used routinely
  for iterating on code changes; whatever systemd setup is added must not fight with that (e.g.,
  a systemd unit set to auto-restart could immediately relaunch a manually-`make stop`'d process,
  or two competing processes could both bind the same port).
- **Ordering matters.** Backend depends on Postgres being reachable; frontend proxies to backend.
  Units should express that dependency (`After=`/`Requires=` or a startup retry/backoff baked
  into the app itself) so a fast boot doesn't have the app crash-loop against a DB that isn't
  ready yet.
- **Should respect O2's firewall sequencing** — no requirement to block on `ufw` explicitly (it's
  already boot-persistent per `feature-018`), but planning should note if there's any startup-race
  concern worth flagging.
- **Secrets handling** — backend reads `backend/.env` (DB creds, `GEMINI_API_KEY`, etc.) today via
  whatever the current process env-loading mechanism is; a systemd unit needs `EnvironmentFile=`
  or equivalent that doesn't regress this or leak secrets into `systemctl status`/journal output.
- This is an infrastructure change — per `CLAUDE.md` governance, requires explicit CEO approval
  before implementation begins.

## Out of scope

- Postgres container supervision (already handled by Docker).
- nginx/SSL/domain/CI-CD (separate, later roadmap steps).
- Closing port 3000 (O5, deferred to post-OSS-launch).
- SSH hardening (O6, separate backlog item).

