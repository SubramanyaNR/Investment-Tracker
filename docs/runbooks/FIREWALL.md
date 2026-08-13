# Runbook — host firewall (`ufw` + `ufw-docker`)

> Status: **live** on the production VPS (`167.233.141.50`). Implements roadmap `O2` /
> `feature-018`. See `.ai-sdlc/artifacts/feature-018/` for the full planning/QA record.

## What's in place

- `ufw` active, `systemctl`-enabled (persists across reboot), default-deny incoming:
  - `22/tcp` (SSH) — allowed
  - `3000/tcp` (frontend) — allowed, deliberate per roadmap `O5` (open-by-default so a fresh
    `git clone` + `docker-compose up` works for self-hosters; closed only on the founder's own
    instance after OSS launch)
  - `tailscale0` (all traffic) — allowed, required for `O4`'s private HTTPS access path
  - Everything else denied by default, including `5432`/`5433` (Postgres) — this was the
    triggering incident (BSI/CERT-Bund flagged `0.0.0.0:5432` exposure 2026-08-06).
- `ufw-docker` installed (patches `/etc/ufw/after.rules` with a `DOCKER-USER` chain routed
  through `ufw`'s decision chain — `# BEGIN/END UFW AND DOCKER` markers). Docker's own iptables
  manipulation is well known to bypass plain `ufw` rules for published container ports; this
  closes that gap. Currently no live Docker-published ports need protecting (both Postgres
  containers are already `127.0.0.1`-bound, backend/frontend run as bare processes, not
  containers) — this is forward-looking cover for the future containerized deploy (`B1`,
  `docs/runbooks/DEPLOY.md`) and for any future compose edit that accidentally republishes a
  port on `0.0.0.0`.

Verify current state any time with:
```bash
sudo ufw status verbose
sudo grep -A2 "BEGIN UFW AND DOCKER" /etc/ufw/after.rules
```

## Re-verification (run after any of these events)

Docker package upgrades and compose recreates have a known history of disturbing `ufw-docker`'s
iptables patch. Re-check after: `apt upgrade docker-ce*`, `docker compose down && up`, or a host
reboot.

From **outside** the VM:
```bash
nmap -p 22,3000,5432,5433 167.233.141.50
# expect: 22 open, 3000 open, 5432 closed/filtered, 5433 closed/filtered
```

On the VM:
```bash
sudo ufw status verbose        # rules still active, default deny (incoming)
systemctl is-enabled ufw       # enabled
```

Tailscale: from a device on the tailnet, load the founder's `*.ts.net` URL — confirms
`tailscale0` traffic isn't blocked.

## Rollback

`sudo ufw disable` restores prior (fully open) connectivity immediately if anything needs to be
undone. Since `ufw enable` was never re-run destructively without a verified second SSH session
first, there is no known lockout scenario in the current config — SSH (`22/tcp`) is allowed and
the rule was verified active from a second, independent session before the first was closed.

## SSH lockout fallback (if a future rule change goes wrong)

Hetzner Robot Rescue system: reboot into a network-booted recovery OS (root password reset via
the Hetzner panel), mount the real disk, `chroot`, fix/disable the bad `ufw` rule, reboot back to
normal boot. Real recovery path, costs a reboot + a few minutes of downtime — not a live console.
A separate VNC/serial Cloud Console may also be available (faster) but wasn't confirmed for this
box as of 2026-08-13.
