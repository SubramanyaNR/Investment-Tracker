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