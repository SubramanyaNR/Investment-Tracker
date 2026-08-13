# Feature Request: Host Firewall with ufw-docker

## User Request

"host firewall with ufw-docker"

## Context

This is `O2` in `docs/product/FEATURE-BACKLOG.md` / step 2 in `docs/product/ROADMAP.md`'s
operational hardening sequence (Operational Hardening — Personal Instance, added 2026-08-06).

Background:
- This VM (`167.233.141.50`, Hetzner) is the founder's actual live personal instance of
  WealthSignal, not a build/reference box (`[[this-vm-is-the-production-vps]]`).
- Triggering incident: BSI/CERT-Bund flagged the self-host sandbox Postgres container publicly
  exposed on `0.0.0.0:5432` on 2026-08-06, fixed same day by rebinding to `127.0.0.1`. Nothing
  at the OS level would have caught this — only the container's own bind address stood between
  Postgres and the public internet.
- Today, `ufw` is installed but inactive. The only thing gating inbound traffic is Docker's own
  iptables rules (whatever `docker-compose` port mappings say). There is no default-deny host
  firewall as a second layer of defense.
- Docker manipulates iptables directly and is well known for bypassing plain `ufw` rules — a
  container's exposed port is exposed regardless of `ufw`'s own `INPUT` chain, unless configured
  specifically to route through it. `ufw-docker` is a widely-used community script that patches
  `ufw`'s `after.rules` so Docker-published ports are actually subject to `ufw` allow/deny
  decisions instead of silently bypassing them.

## Goal

Default-deny host firewall: block all inbound traffic except explicit allows, with Docker
container ports actually subject to those rules (not bypassing them).

Required allows (current known exposure surface):
- SSH (whatever port is actually configured — verify, don't assume 22)
- App port 3000 (frontend) — must stay reachable per the step 8 / O5 "out-of-the-box `docker-compose
  up`" decision (`docs/product/ROADMAP.md` step 8, `FEATURE-BACKLOG.md` O5) — this is deliberate,
  not an oversight to close now.
- Tailscale interface (`tailscale0`) — must not be blocked; O4 (`docs/product/ROADMAP.md` step 4)
  is the founder's private HTTPS access path and depends on Tailscale traffic reaching the host.

Everything else inbound should be denied by default, including Postgres (5432) which must remain
unreachable from outside regardless of any future docker-compose misconfiguration — this is the
actual containment goal, a repeat of the triggering incident should not be able to happen even if
a port mapping mistake is made again.

## Constraints / concerns to address in planning

- **Must not lock out SSH access to the VM.** This is a remote-only Hetzner box with no console
  access mentioned elsewhere in project docs — an `ufw` misconfiguration that blocks SSH before
  the rule allowing it is confirmed active would be a severe, possibly unrecoverable (without
  provider console access) incident. Plan must sequence rule application so SSH access is never
  dropped mid-change, and should state whether Hetzner console/rescue access exists as a fallback.
- **Must not break Tailscale (O4)** or the intentionally-open port 3000 (O5/step 8) — this is a
  firewall to contain *unintended* exposure (like the Postgres incident), not to re-close ports
  the founder deliberately decided to leave open.
- `ufw-docker` specifically patches Docker's iptables integration — planning should confirm this
  is the right/current approach (vs. alternatives like binding all container ports to
  `127.0.0.1` explicitly, or Docker's own `--publish 127.0.0.1:...` per-port binding) and note
  any maintenance burden (e.g., does it need to be reapplied after Docker restarts/upgrades).
- This is an infrastructure change — per `CLAUDE.md` governance, requires explicit CEO approval
  before implementation begins.

## Out of scope

- Process supervision (systemd units) — separate roadmap step (3), not this request.
- Closing port 3000 — deferred to O5, gated on OSS GitHub release, not part of this firewall work.
