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

## Post-restart application-level check (2026-08-13, follow-up)

After a further manual restart to confirm a fix, checked that the app is actually functional
under the new systemd supervision, not just that the units are `active`:

- `investment_tracker_postgres` container: up, `healthy`.
- `it-backend` / `it-frontend`: both `active (running)`, started cleanly, `ExecStartPre`
  `pg_isready` wait succeeded (no crash-loop against a cold DB).
- `POST /auth/login` (direct, `127.0.0.1:8000`) with the bootstrap admin credentials from
  `backend/.env` → `200`, sets `access_token`/`refresh_token`/`csrf_token` cookies.
- `GET /auth/me` with the resulting session cookie → `200`, resolves the correct `user_id`.
- Same login flow repeated through the frontend `/api` proxy (`<vps-ip>:3000/api/auth/login`,
  `[[frontend-accessed-by-vm-ip-via-api-proxy]]`) → `200`, identical `user_id` — confirms the
  proxy path works end-to-end under systemd, not just the direct backend port.

Login path fully functional post-restart under systemd supervision. Does not change the
"Not verified — needs a real reboot" item above (this was a manual `systemctl restart`, not a host
reboot) — boot-time auto-start is still the one open acceptance criterion.

## Verdict

Core process-supervision behavior (crash recovery, clean-stop safety, Makefile repoint) verified
directly and correct. Application-level login flow confirmed working post-restart, including via
the frontend proxy. One acceptance criterion — actual reboot persistence — still needs to be run
for real before this is fully closable; recommend as a manual validation item.
