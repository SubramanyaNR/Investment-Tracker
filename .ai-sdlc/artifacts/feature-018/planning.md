# Review: Host Firewall with ufw-docker (O2)

## Verdict
Sound, well-scoped infrastructure hardening request. The reasoning is correct on the core technical point (Docker bypasses `ufw`'s INPUT chain by manipulating iptables `DOCKER` chains directly), the containment goal is well-justified by the actual incident, and the constraints section already anticipates the two things most likely to cause harm (SSH lockout, breaking Tailscale/3000). This is close to implementation-ready pending CEO approval. A few gaps worth closing before that approval is sought.

## Technical / Architecture

**`ufw-docker` is the right call, but confirm currency before relying on it.** It's the standard community fix for this exact problem (patching `after.rules` to route `DOCKER-USER`/published-port traffic through `ufw`'s decision chain). The alternative floated in the request — binding container ports to `127.0.0.1` per-service in `docker-compose.yml` — is actually the *more robust* primary control and isn't mutually exclusive with `ufw-docker`; worth doing both rather than treating them as either/or:
- `127.0.0.1` binding in compose is declarative, versioned, reviewable in PRs, and doesn't depend on a third-party script surviving Docker upgrades.
- `ufw-docker` is the safety net for services that *do* need to be host-reachable (3000) and for anything a future compose change accidentally publishes on `0.0.0.0`.

Given the triggering incident was exactly "a port mapping mistake," defense-in-depth (compose binding + ufw-docker) is more consistent with the stated goal ("must remain unreachable... even if a port mapping mistake is made again") than ufw-docker alone. Recommend the plan explicitly say which services get `127.0.0.1`-bound in compose vs. rely solely on the firewall layer.

**Maintenance burden not yet answered, and it should be before approval, not during implementation.** `ufw-docker`'s known failure mode is silent regression: Docker restarts can re-flush/reorder iptables rules, and `ufw-docker` needs to be reapplied or run as an install step (`ufw-docker install`) that persists via the `after.rules` file — it generally survives reboots once installed correctly, but Docker package upgrades have historically broken it (there are open upstream issues about this depending on Docker version). The plan should include a **post-install verification step** (e.g. attempt an external connection to 5432 from off-host, confirm it's refused, re-check after any `apt upgrade docker-ce` or `docker compose down/up`) rather than a one-time "install and forget." This is exactly the kind of thing that should go in the runbook, not just be done once.

## SSH Lockout Risk (highest-severity concern)

The request correctly flags this but doesn't yet commit to a sequence. Recommend the plan state explicitly, in order:
1. Verify actual SSH port in use (don't assume 22) — check `sshd_config` and any cloud-init/Hetzner firewall config.
2. Add the `ufw allow <ssh-port>/tcp` rule **and confirm it's active** (`ufw status verbose`) *before* `ufw enable` is ever run, not just before other allow rules.
3. Keep the current SSH session open and open a **second, independent** SSH session after `ufw enable` to confirm access before closing the first. Never rely on a single session as the rollback path.
4. State plainly whether Hetzner Cloud Console/rescue system access exists as a fallback (Hetzner Cloud VMs do have a serial/VNC console independent of network — this should be confirmed and documented, not assumed, since the request notes it's unconfirmed).

Absent Hetzner console confirmation, this is a single-mistake-away-from-full-lockout change on a box with real user data and no stated recovery path. That alone should be treated as a go/no-go gate for the CEO approval, not just a planning note.

## Product / Investor Experience

No end-user-facing surface — correctly scoped as pure infra. No concerns here beyond noting that any downtime during the cutover (even seconds) affects a real, currently-in-use personal instance, not a staging box. Worth a one-line "expected downtime: none if sequenced correctly / a few seconds of SSH session risk during enable" in the plan so the CEO approval is informed about blast radius, not just mechanism.

## QA / Validation

The plan needs explicit test cases before being called complete, e.g.:
- External scan (from outside the VM, e.g. `nmap` or `curl` from another host) confirming 5432 is unreachable, 3000 is reachable, SSH port is reachable.
- Confirm Tailscale traffic (via `tailscale0`) still functions — e.g. `tailscale ping`/access an internal service over the tailnet — post-enable.
- Confirm `docker compose down && docker compose up -d` doesn't silently reopen 5432 (this is the actual regression `ufw-docker` is meant to prevent — test it, don't just assume the patch holds).
- Confirm firewall rules persist across a host reboot (`ufw` is systemd-enabled by default, but verify).

None of this needs to happen now — it belongs in the SDLC QA stage — but the plan document should name these as acceptance criteria up front.

## Governance

Correctly identified as requiring CEO approval (infrastructure change, per CLAUDE.md gate list). Nothing to add here except: the SSH-lockout fallback question (Hetzner console access) should be answered *before* the approval request goes up, since it materially changes the risk being approved.

## Summary of asks before this goes to approval
1. ~~Confirm Hetzner console/rescue access as an SSH fallback.~~ **Confirmed 2026-08-13.** Hetzner
   Robot has a Rescue system: reboot into a network-booted recovery OS (root password reset via
   panel), mount the real disk, `chroot`, fix/disable the bad `ufw` rule, reboot back to normal
   boot. Real recovery path, not a permanent lockout — but costs a reboot + a few minutes of
   downtime + manual steps, it is not a live console into the running system. (Hetzner also
   typically offers a separate VNC/serial Cloud Console, independent of network, which would be
   faster if available — not yet confirmed for this box.) Net: SSH-lockout risk is recoverable,
   go/no-go gate is satisfied.
2. **Compose-level `127.0.0.1` binding — checked against actual running state 2026-08-13.**
   `docker ps` shows both currently-running Postgres containers already `127.0.0.1`-bound:
   `investment_tracker_postgres` (real data, `docker-compose.local.yml`) on `127.0.0.1:5433`,
   `investment_tracker_selfhost_postgres` (sandbox, `docker-compose.selfhost.yml`) on
   `127.0.0.1:5432`. No compose change needed there — this is already the state the original
   incident fix put us in. Backend (`8000`) and frontend (`3000`) are **not** Docker containers
   today; they run as bare `nohup` processes (O3), so Docker's iptables/`ufw` bypass doesn't apply
   to them — plain `ufw allow` rules govern them directly and correctly.
   `docker-compose.yml` (root) *does* define `backend`/`frontend` services publishing `8000` and
   `3000` on `0.0.0.0`, but its own header states it is not the current deploy path — it's the
   target for the future fully-containerized deploy (roadmap B1, `docs/runbooks/DEPLOY.md`).
   Recommendation: no change to that file now; when B1 lands, bind backend's `8000` to
   `127.0.0.1:8000:8000` (no reason for it to be host-reachable — only the frontend proxies to it)
   and keep frontend's `3000` published-but-`ufw-docker`-gated. File as a B1 implementation note,
   not O2 scope.
   Net: `ufw-docker` has no live Docker-published-port exposure to protect against *today* — its
   value here is purely forward-looking, as the safety net for the B1 containerized deploy and for
   any future compose edit that accidentally republishes Postgres on `0.0.0.0`. Still worth
   installing now per the original request's containment goal ("must remain unreachable... even if
   a port mapping mistake is made again"), since it's a one-time install and the failure mode it
   guards against is exactly the triggering incident.
3. **Re-verification step.** Add to `docs/runbooks/DEPLOY.md` (or a new `FIREWALL.md` runbook,
   implementer's call): after any `apt upgrade docker-ce*`, `docker compose down && up`, or host
   reboot, re-run from an external host: `nmap -p 22,3000,5432,5433 167.233.141.50` (or `curl -m3`
   per port) confirming 22/3000 open and 5432/5433 closed, plus `ufw status verbose` confirming
   rules still active. This is a recurring manual check, not automated monitoring — acceptable
   given this is a personal instance, but should be written down so it isn't forgotten after the
   next `docker compose up`.
4. **Rule-application order (SSH-lockout-safe sequence), using confirmed values (SSH port `22`,
   `sshd_config` has `#Port 22` commented = default in effect; `ufw` currently `inactive`):**
   1. `ufw allow 22/tcp` (SSH)
   2. `ufw allow 3000/tcp` (frontend, per O5's deliberate open-by-default decision)
   3. `ufw allow in on tailscale0` (must not block O4's private HTTPS path)
   4. `ufw default deny incoming`, `ufw default allow outgoing`
   5. `ufw show added` — confirm the four rules above are staged, *before* enabling
   6. `ufw enable`
   7. In the **existing** SSH session: `ufw status verbose` — confirm 22 and 3000 show `ALLOW`,
      Tailscale interface not blocked, default is `deny (incoming)`.
   8. **Without closing that session**, open a brand-new, independent second SSH connection from
      the local machine to the VM's public IP on 22. Confirm it connects and authenticates.
   9. Only after the second session is confirmed, close the first.
   10. Then run `ufw-docker install` (patches `after.rules`, reloads `ufw`) — repeat steps 7–9
       (two-session re-verification) after this step too, since it reloads firewall state.
5. **Acceptance tests (QA stage):**
   - External scan (from outside the VM, e.g. `nmap`/`curl` from another host) confirming: `22`
     reachable, `3000` reachable, `5432` and `5433` unreachable, no other unexpected open ports.
   - Tailscale check: from the founder's phone (on the tailnet), load the `*.ts.net` URL — confirms
     `tailscale0` traffic isn't blocked.
   - Docker regression check: `docker compose -f docker-compose.local.yml down && up -d` (the real
     Postgres container), then re-scan `5433` externally — confirms `ufw-docker` survives a
     container recreate, not just the initial install.
   - Reboot persistence: reboot the VM, confirm `systemctl is-enabled ufw` is `enabled` and
     `ufw status verbose` shows the same rules post-boot; re-run the external scan.
   - Rollback check: confirm `ufw disable` restores prior connectivity, in case anything needs to
     be undone quickly.