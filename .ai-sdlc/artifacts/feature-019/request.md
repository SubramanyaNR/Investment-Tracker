# Feature Request: Process Supervision (systemd units)

## User Request

"start O3 process supervision"

## Context

This is `O3` in `docs/product/FEATURE-BACKLOG.md` / step 3 in `docs/product/ROADMAP.md`'s
operational hardening sequence (Operational Hardening — Personal Instance, added 2026-08-06).

Background:
- This VM (`167.233.141.50`, Hetzner) is the founder's actual live personal instance of
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

## Decisions (CEO-approved 2026-08-13, resolving planning.md "Gaps to close")

1. **Service user: `root`.** Matches current de facto ownership (bare `nohup` already runs as
   root today) — no permission/chown changes needed.
2. **Makefile repointed to systemd.** `make backend`/`make frontend`/`make stop`/`make restart`
   become thin wrappers around `systemctl start/stop/restart it-backend`/`it-frontend`, so there
   is exactly one process-management path — no foot-gun where a manual `kill` gets silently
   resurrected by systemd's auto-restart. `make dev`/`make logs`/`make validate` behavior should
   stay equivalent from the user's point of view (start both, tail logs, health-check).
3. **Postgres readiness: rely on `Restart=on-failure`, no explicit wait loop.** Confirmed
   `backend/app/main.py`'s `lifespan` calls `bootstrap_admin_user()` at startup with no existing
   DB-retry logic — a not-yet-ready Postgres will crash the process hard, which `Restart=on-failure`
   + `RestartSec=` already handles (just a few extra seconds on a fast boot, no special-casing
   needed). `After=docker.service` for ordering hint only.
4. **Logs: journal only.** `journalctl -u it-backend` / `-u it-frontend`, not `/tmp/it-*.log` —
   avoids double-writing/rotation conflicts. `make logs` should be updated to `journalctl -f` both
   units instead of tailing the old files.

## Out of scope

- Postgres container supervision (already handled by Docker).
- nginx/SSL/domain/CI-CD (separate, later roadmap steps).
- Closing port 3000 (O5, deferred to post-OSS-launch).
- SSH hardening (O6, separate backlog item).
