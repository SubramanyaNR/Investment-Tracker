# Runbook — process supervision (systemd)

> Status: **live** on the production VPS (`<vps-ip>`). Implements roadmap `O3` /
> `feature-019`. See `.ai-sdlc/artifacts/feature-019/` for the full planning/QA record.

## What's in place

Backend (`uvicorn`) and frontend (`next start`) each run as a systemd unit — no more bare
`nohup`/PID-file processes:

- `deploy/systemd/it-backend.service` — `ExecStart` the venv's `uvicorn`, `EnvironmentFile=`
  points at `backend/.env` (secrets loaded via systemd's own mechanism, never baked into the
  unit file or visible in `systemctl status`/journal).
- `deploy/systemd/it-frontend.service` — `ExecStart=/usr/bin/npm start`, `After=it-backend.service`.
- Both: `User=root` (matches prior de facto ownership — no ownership change to the app dir/venv),
  `Restart=on-failure`, `RestartSec=5`, `StartLimitIntervalSec=60`/`StartLimitBurst=5` (stops
  retrying after 5 crashes/minute rather than looping forever), `enabled` (auto-start on boot).
- Logs go to the journal only — `journalctl -u it-backend -u it-frontend`, not
  `/tmp/it-*.log` anymore (avoided a double-write/rotation conflict with the old Makefile
  redirection).

## Day-to-day usage — Makefile repointed to systemctl

`make backend` / `make frontend` / `make dev` / `make restart` / `make stop` /
`make stop-backend` / `make stop-frontend` / `make logs` all now wrap `systemctl`
start/stop/restart and `journalctl -f` — **do not call `systemctl` directly for routine dev
iteration**, use the Makefile targets so there's exactly one process-management path. (Direct
`systemctl`/`journalctl` calls are fine for inspection — `status`, `is-active`, `is-enabled` —
just not for starting/stopping.)

- `make backend` — rebuild-free restart, picks up backend code changes.
- `make frontend` — runs `npm run build` first, then restarts the unit so the new build is
  actually served (`next start` reads the compiled `.next/` output once at process start; a
  rebuild alone doesn't hot-swap it).
- `make stop-backend` / `make stop-frontend` / `make stop` — a `systemctl stop` is a *clean*
  stop; `Restart=on-failure` does **not** trigger on a clean stop signal, only on a non-zero
  exit/crash. So `make stop` reliably stays stopped — verified in this session (killed via
  `systemctl stop`, confirmed `inactive` after 3s, no resurrection).

## Postgres readiness

No `ExecStartPre` wait-loop. `backend/app/main.py`'s `lifespan` calls `bootstrap_admin_user()`
at startup with no existing DB-retry logic — if Postgres isn't reachable yet, the process exits
non-zero and `Restart=on-failure` + `RestartSec=5` recovers it a few seconds later once Postgres
is up. `After=docker.service` is an ordering hint only, not a readiness guarantee — acceptable
here since the failure mode is "a few seconds slower to come up," not data loss or corruption.

## Verified this session (2026-08-13)

- Both units start clean, `systemctl status` shows `active (running)`.
- `make validate` passes (backend `/health` ok, frontend serving).
- **Crash recovery**: `kill -9` on the backend's main PID → systemd restarted it within ~2s
  (new PID, restart counter incremented in `systemctl status`).
- **Clean stop doesn't resurrect**: `make stop-backend` (`systemctl stop`) → confirmed
  `inactive` after 3s, not auto-restarted.
- `systemctl is-enabled it-backend it-frontend` → both `enabled` (will auto-start on next boot;
  not yet exercised via an actual reboot in this session — first real boot will confirm).

## Reinstalling / updating the units

If `deploy/systemd/*.service` changes:
```bash
make install-services   # copies to /etc/systemd/system/, daemon-reload, enable
make restart             # picks up the new unit definitions
```

## Rollback

`systemctl disable --now it-backend it-frontend` stops both and removes boot auto-start,
reverting to a state where nothing runs until manually started. The old `nohup`-based Makefile
recipes are fully replaced, not kept in parallel — if a rollback to bare-`nohup` is ever needed,
restore the previous `Makefile` targets from git history (pre-`feature-019`).
