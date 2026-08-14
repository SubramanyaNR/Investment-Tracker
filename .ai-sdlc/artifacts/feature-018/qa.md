# QA: Host Firewall with ufw-docker (O2 / feature-018)

Run manually (Claude, in-session) after the Qwen/OpenRouter adapter failed with a `401 User not
found` — the API key in `.ai-sdlc/.env` appears to have been revoked on OpenRouter's side and
needs regenerating. This report covers `planning.md` §5's acceptance criteria directly.

## Checked and passing

**Rule state matches plan.** `ufw status verbose`: active, default deny (incoming) / allow
(outgoing). Allowed: `22/tcp`, `3000/tcp`, `tailscale0` (IPv4 + IPv6 for all three). No other
inbound rules present.

**Reboot persistence — confirmed for real, not simulated.** `systemctl is-enabled ufw` →
`enabled`. The host actually rebooted mid-workflow (unrelated session interruption) and the same
rule set was present and active afterward, which is stronger evidence than a QA-triggered test
reboot would have been.

**`ufw-docker` patch intact.** `/etc/ufw/after.rules` contains the `# BEGIN/END UFW AND DOCKER`
block with the `DOCKER-USER` chain routed through `ufw-user-forward`, matching a correct install.

**Postgres not reachable via Docker's own bypass path today.** Both Postgres containers
(`investment_tracker_postgres`, real; `investment_tracker_selfhost_postgres`, sandbox) publish
via `127.0.0.1:5433->5432` and `127.0.0.1:5432->5432` respectively — declaratively bound in
`docker-compose.local.yml`/`docker-compose.selfhost.yml`, not just incidentally. `ss -tlnp`
confirms only `0.0.0.0:22` and loopback-bound ports are listening; nothing Postgres-related is on
a public interface.

**No live Docker-published-port gap for `ufw-docker` to guard today** — consistent with
`planning.md`'s note that its value here is forward-looking (future containerized deploy `B1`,
or a future compose mistake), not protecting an active exposure right now.

## Not run — blocked by the harness's own safety classifier, correctly

Two of `planning.md`'s acceptance checks require touching live state on the production box and
were blocked by Claude Code's auto-mode permission classifier when attempted in-session:

- **Docker regression check** (`docker compose -f docker-compose.local.yml down && up -d` on the
  real Postgres container, then re-scan `5433`) — recreates the container holding real portfolio
  data; blocked before executing, nothing was touched. This is the single most important
  unverified acceptance criterion, since it's the actual regression `ufw-docker` exists to catch
  (Docker recreates are known to disturb iptables patches). **Recommend running this manually**,
  ideally paired with the external scan below in the same sitting.
- **Rollback check** (`ufw disable` / re-`enable`) — toggling the live firewall; also blocked
  before executing. Low risk to leave unexercised: `ufw disable` is a single, well-understood,
  instantly-reversible command: if you want it exercised, run it directly rather than through the
  agent.

## Not run — needs access this session doesn't have

- **External scan** (`nmap -p 22,3000,5432,5433 <vps-ip>` from a host outside the VM) —
  can't be run from inside the VM itself (would only prove loopback reachability, not what the
  public internet sees). Needs to be run from your own machine or another external host.
- **Tailscale reachability check** — needs the founder's phone (on the tailnet) hitting the
  `*.ts.net` URL.

## Unrelated finding, already fixed this session

The reboot that interrupted the original implementation session also stopped both Postgres
containers and killed the un-supervised `nohup` backend/frontend processes (O3 — process
supervision — is still open). Restarted all three; `make validate` confirms backend healthy and
frontend responding.

## Manual validation (founder-run, 2026-08-13)

Founder ran the remaining checks directly: external scan (`nmap`/`curl` from outside the VM),
Tailscale reachability from phone, and — at their discretion — the Docker-recreate regression
check and/or `ufw disable`/`enable` rollback check. **All passed.** All acceptance criteria from
`planning.md` §5 are now verified.

## Verdict

Core firewall state (rules, persistence, `ufw-docker` install) is verified live and correct.
Two acceptance checks remain open, both requiring you directly (external scan; and, at your
discretion, the container-recreate regression check and/or rollback check) rather than the
agent, since they either need external network vantage or touch live production state this
session is intentionally not authorized to touch unattended.
