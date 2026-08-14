# Audit Prompt

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


## Security Context
# Security Context

Authentication & Isolation:
- Supabase Auth for token issuance.
- ES256 JWT verification in backend.
- Multi-tenancy: Every user-owned table has 'user_id' (NOT NULL).
- RLS policy: 'tenant_isolation' keyed on 'app.current_user_id' GUC.
- Ownership checks return 404 for missing or unauthorized resources.


## Investor Experience Context
# Investor Experience Context

Investor Trust & Clarity:
- Metric comprehension: Are units and calculations clear?
- Dashboard clarity: Mobile-first status at a glance.
- Investor trust: Presentation must build confidence; limitations must be clear.
- Presentation of insights: Language must be investor-friendly, not overly technical.


## Planning
**Product**
Solid, unambiguous personal-instance goal — availability after a reboot is a real trust issue (an app that's silently down fails "portfolio observability" at the moment it's checked). Correctly scoped: no user-facing surface, so this is closer to an infra ADR than a product feature.

**Technical / Architecture**
- The plan correctly identifies the two failure modes worth designing against: crash-loop against a not-yet-ready Postgres, and systemd fighting `make dev`/`make stop`. Both are real and specific to this setup (bare nohup + Makefile PID files today).
- `Restart=on-failure` with backoff (`RestartSec=`, and ideally `StartLimitIntervalSec=`/`StartLimitBurst=`) is the right call over `Restart=always` — avoids restart storms if the app has a persistent bug.
- Ordering: `After=docker.service` plus a check that the Postgres container is actually accepting connections (not just that Docker is up) is the subtlety to get right — `After=` alone only orders unit start, not readiness. Recommend either an `ExecStartPre` wait-for-Postgres check or relying on the app's own retry/backoff at startup (the request already flags this as acceptable).
- `EnvironmentFile=` pointing at `backend/.env` is correct and avoids the leak risk of baking secrets into the unit file itself (unit files are typically world-readable in `/etc/systemd/system`; env files loaded via `EnvironmentFile=` are not printed by `systemctl status`, but confirm perms on the `.env` file itself, e.g. `600`, owned by the service user).
- The dev-workflow conflict is the sharpest risk here: if systemd owns ports 8000/3000 with auto-restart, `make stop`/`make restart` doing `kill $(cat pid)` will just get resurrected by systemd within `RestartSec`. The plan's framing — repoint Makefile targets at `systemctl start/stop`, or leave Makefile for local/dev only with systemd strictly as boot/crash-recovery — is the right question to force, but it needs an actual answer before implementation, not just "implementer's call." I'd lean toward repointing `make backend`/`make frontend`/`make stop`/`make restart` to call systemctl (via `sudo systemctl restart it-backend` etc.), since leaving two independent process-management paths pointed at the same ports is a foot-gun that will bite exactly when someone's mid-iteration and forgets systemd exists.
- Running the units as a non-root systemd user service (or root unit with `User=`) should be made explicit — nothing in the request specifies this, and it affects file permissions and the sudo requirement for the repointed Makefile targets.

**Investor Experience**
No direct UI surface, but indirectly this *is* an investor-trust feature: uptime after unattended reboots. No further investor-facing considerations.

**Governance**
Correctly flagged as infrastructure requiring CEO approval per CLAUDE.md — this is a process-supervision/production-topology change, gated. Recommend the approval ask explicitly include the Makefile-repoint decision (systemd-owns-ports vs. Makefile-owns-ports for dev) as a decision point, not leave it implicit, since that choice has real day-to-day workflow impact.

**Gaps to close before/at approval**
1. Decide service user (root vs dedicated non-root user) for the two units.
2. Decide explicitly: Makefile targets get repointed to `systemctl`, or stay independent with a documented "don't use both" warning.
3. Confirm Postgres readiness handling — `ExecStartPre` wait loop vs. relying on app-level DB retry (check whether uvicorn/FastAPI startup currently retries on DB connection failure or crashes hard — if it crashes hard, `Restart=on-failure` + `RestartSec` alone is sufficient without an explicit wait, just slower to recover).
4. Log destination decision (journal vs. `/tmp/it-*.log`) should probably be journal-only for the systemd path, to avoid double-writing/rotation conflicts with the Makefile's own log redirection.

## Implementation
# Implementation: Process Supervision (systemd) — O3

## Status
Live on the production VPS (`<vps-ip>`) as of 2026-08-13. Implemented directly by Claude
(not the Gemini adapter — daily free-tier quota for `generativelanguage.googleapis.com` was
already exhausted today from `feature-018`'s implementation runs; same failure mode, documented
in memory as a known limitation).

## What was done
1. Confirmed the four CEO-approved decisions from `request.md`: service user `root`, Makefile
   repointed to `systemctl`, no `ExecStartPre` wait-loop (confirmed `bootstrap_admin_user()` in
   `backend/app/main.py`'s `lifespan` has no DB-retry, crashes hard — `Restart=on-failure` alone
   is sufficient), journal-only logs.
2. Added `deploy/systemd/it-backend.service` and `deploy/systemd/it-frontend.service` —
   `Restart=on-failure`, `RestartSec=5`, rate-limited via `StartLimitIntervalSec=60`/
   `StartLimitBurst=5`, `EnvironmentFile=` for backend secrets, `enabled` for boot auto-start.
3. Added `make install-services` target; repointed `backend`/`frontend`/`stop-backend`/
   `stop-frontend`/`stop`/`dev`/`restart`/`logs` to wrap `systemctl`/`journalctl` instead of
   `nohup`/PID files.
4. Cut over live: installed + enabled the units, stopped the old `nohup` processes, started both
   via `systemctl`, confirmed healthy via `make validate`.
5. Wrote `docs/runbooks/PROCESS-SUPERVISION.md`.

## Verified in this session
- Both units `active (running)` after cutover; `make validate` passes.
- **Crash recovery**: `kill -9` on backend's main PID → systemd auto-restarted within ~2s.
- **No restart storm on clean stop**: `make stop-backend` → confirmed `inactive` after 3s, not
  resurrected — resolves the dev-workflow conflict risk the planning stage flagged as sharpest.
- `systemctl is-enabled` → both `enabled` (boot auto-start configured).

## Not yet verified
- **Actual reboot test** — boot-time auto-start is configured (`enabled`) but not exercised via
  a real reboot in this session (didn't want to trigger another unplanned outage right after
  `feature-018`'s reboot incident). First real reboot will confirm; flagged for QA/manual
  validation.
- **Frontend crash recovery** — only backend's `kill -9` recovery was tested directly; frontend
  uses the same `Restart=on-failure` mechanism, same expected behavior, not independently
  exercised.

## Scope note
Postgres container supervision was explicitly out of scope (already Docker-managed). No changes
to `docker-compose*.yml`, firewall, or auth.


## Code Review
<!-- Artifact template: code review findings -->


## QA
# QA: Process Supervision (systemd) — O3 / feature-019

Run manually (Claude, in-session) — the Qwen/OpenRouter adapter returned the same `401 User not
found` seen on `feature-018` (key still not fixed; account-level issue, not transient).

## Checked and passing

- Both `it-backend` and `it-frontend` units `active (running)`, `enabled` (boot auto-start
  configured). `make validate` passes (backend `/health` ok, frontend serving).
- **Crash recovery (backend)**: `kill -9` on the main PID → systemd restarted within ~2s, new
  PID, restart counter incremented in `systemctl status`. Directly exercised in-session.
- **Clean stop doesn't resurrect**: `make stop-backend` (→ `systemctl stop`) → confirmed
  `inactive` 3s later, not auto-restarted. This was the sharpest risk the planning stage flagged
  (systemd fighting manual dev stop/restart) — resolved, verified.
- **Makefile repoint correct**: `make backend`/`make frontend`/`make dev`/`make stop`/`make logs`
  all route through `systemctl`/`journalctl`, matches the approved decision. No leftover
  `nohup`/PID-file paths.
- `EnvironmentFile=backend/.env` — confirmed secrets aren't printed in `systemctl status` output
  for either unit.
- pytest (unit, non-integration) passes, 0 files newly touched outside `deploy/systemd/` +
  `Makefile` + docs — matches the declared scope (no backend/frontend app code changes).

## Not verified — needs a real reboot

Boot-time auto-start (`enabled`) was not exercised via an actual reboot in this session —
deliberately avoided triggering another unplanned outage right after `feature-018`'s reboot
incident. This is the one acceptance criterion that can't be faked: **recommend a real reboot at
a convenient time, followed by `systemctl is-active it-backend it-frontend` + `make validate`**
to close this out.

## Not independently verified

- **Frontend crash recovery** — only backend's `kill -9` was tested directly. Frontend runs under
  the same `Restart=on-failure` mechanism with no reason to expect different behavior, but wasn't
  exercised separately.

## Observation, out of scope, logged not fixed

Backend journal shows a burst of `404`s for paths like `/trpc`, `/auth/get-session`,
`/trpc/settings.ai`, `/config`, `/status` — signatures of automated scanners probing for
Next.js/tRPC/`better-auth` apps (a different stack than this one). Backend is `127.0.0.1`-bound
so not directly reachable externally; unclear from this session alone whether these are hitting
the backend directly (localhost-only, so only from something on-box) or arriving via the
frontend's `/api` proxy forwarding unrecognized paths through. Not investigated further — outside
O3's scope, worth a security-backlog follow-up to confirm the proxy doesn't blindly forward
arbitrary unauthenticated paths to the backend.

## Verdict

Core process-supervision behavior (crash recovery, clean-stop safety, Makefile repoint) verified
directly and correct. One acceptance criterion — actual reboot persistence — needs to be run for
real before this is fully closable; recommend as a manual validation item.

