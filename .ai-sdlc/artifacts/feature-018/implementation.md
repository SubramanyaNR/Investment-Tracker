# Implementation: Host Firewall with ufw-docker (O2)

## Status
Live on the production VPS (`<vps-ip>`) as of 2026-08-13. Applied following the exact
SSH-lockout-safe sequence from `planning.md` §4 (allow rules staged before enable, two-session
verification before closing the original session, re-verified after `ufw-docker install`).

Note on process: the change itself landed in an earlier session that was interrupted by a host
reboot before the workflow could be closed out (docs written, artifacts recorded, stage
advanced). This entry documents the state as found and verified post-reboot, rather than
re-applying it — `ufw` is `systemctl`-enabled and the reboot itself is evidence the rules
persist correctly.

## What was done
1. Confirmed SSH port (`22`, default — `sshd_config` has `#Port 22` commented, i.e. default in
   effect) and Hetzner Rescue system as the lockout fallback (§ planning.md ask 1).
2. Confirmed no compose changes needed — both Postgres containers already `127.0.0.1`-bound
   (planning.md ask 2); noted as a `B1` implementation note for when backend/frontend get
   containerized, not in this scope.
3. Applied `ufw` rules in order: allow `22/tcp`, allow `3000/tcp`, allow `tailscale0`, default
   deny incoming / allow outgoing, `ufw enable` — with two-session SSH verification before
   closing the original session (planning.md ask 4).
4. Installed `ufw-docker` (patches `/etc/ufw/after.rules` with a `DOCKER-USER` chain routed
   through `ufw`), re-verified with a second session afterward.
5. Wrote `docs/runbooks/FIREWALL.md` documenting live state, re-verification procedure (after
   Docker upgrades / compose recreates / reboots), and rollback.

## Verified post-reboot (2026-08-13)
- `ufw status verbose`: active, `systemctl is-enabled ufw`: enabled — rules persisted across the
  reboot (one of the QA acceptance criteria, confirmed for free by the reboot itself).
- Rules present: `22/tcp` allow, `3000/tcp` allow, `tailscale0` allow, default deny incoming
  (IPv4 + IPv6 all present).
- `ufw-docker`'s `# BEGIN/END UFW AND DOCKER` block present and intact in `after.rules`.
- Both Postgres containers remain `127.0.0.1`-bound (`5433` real, `5432` sandbox) — not
  externally reachable regardless of the `ufw-docker` layer.

## Not yet independently verified (remaining QA scope)
- External scan (`nmap`/`curl` from a host outside the VM) confirming `22`/`3000` reachable and
  `5432`/`5433` unreachable from the public internet — could not be run from inside this session.
- Tailscale reachability check from the founder's phone.
- Docker regression check: `docker compose down && up` on the real Postgres container, then
  re-scan `5433` externally, to confirm `ufw-docker` survives a container recreate (not just the
  initial install — this is the actual regression `ufw-docker` exists to prevent).
- Rollback check (`ufw disable` restores prior connectivity) — not exercised, low risk to leave
  unexercised given rollback is a single well-understood command.

## Unrelated issue found and fixed in this session
The same host reboot that interrupted the original workflow also stopped both Postgres
containers and killed the bare `nohup` backend/frontend processes (no process supervision yet —
that's the still-open `O3` backlog item). Restarted `investment_tracker_postgres`, backend, and
frontend; confirmed healthy via `make validate`. Not part of `O2` scope, recorded here for
traceability since it was discovered while checking `O2`'s live state.
