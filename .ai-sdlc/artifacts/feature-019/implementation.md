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
