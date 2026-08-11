# Feature Request: Tailscale for Private HTTPS Access

## User Request

Set up Tailscale on this VM (`167.233.141.50`) for private HTTPS access via `tailscale cert`.

## Context

This is `O4` in `docs/product/FEATURE-BACKLOG.md` / step 4 in `docs/product/ROADMAP.md`'s
operational hardening milestone. Background:

- This VM is confirmed as the founder's actual live personal instance of WealthSignal (an
  investment portfolio tracker), not just a build/reference box.
- Earlier this week, BSI/CERT-Bund flagged the self-host sandbox Postgres container publicly
  exposed on `0.0.0.0:5432` (already fixed, rebound to `127.0.0.1`). That incident is why
  operational hardening (backups, firewall, process supervision, this Tailscale task) is now
  sequenced ahead of further app feature work.
- The founder decided against buying a public domain / opening a public-facing HTTPS endpoint
  (Nginx + Certbot) for personal-only access, preferring a private-network approach.

## Why this task, and why now (sequencing)

This must land **before** the auth rewrite (`architecture-002` Phase 2, custom bcrypt/JWT auth
replacing Supabase Auth). That rewrite's design already commits to httpOnly + `Secure` cookies and
CSRF protection (SameSite + CSRF token on state-changing requests) — both behave differently under
plain HTTP vs HTTPS. Building and testing that auth work over real TLS from the start (via
Tailscale) avoids retrofitting or silently-broken `Secure` cookie behavior later.

This may also fully replace the need for a public domain (`FEATURE-BACKLOG.md` V2 / `ROADMAP.md`
step 6) — that decision is explicitly deferred until after this task, not part of this task's scope.

## Requirements

- Install and configure Tailscale on this VM, joined to the founder's tailnet.
- Use `tailscale cert` to obtain a real, trusted HTTPS certificate for the VM's Tailscale
  (`*.ts.net`) hostname.
- Serve the app (currently: Next.js frontend on `:3000`, FastAPI backend on `127.0.0.1:8000`
  behind the frontend's `/api` proxy) over HTTPS via this cert — reachable only over the Tailscale
  network, not the public internet.
- **Nothing new should be exposed to the public internet.** No new public-facing ports, no public
  DNS record, no changes to what's currently reachable from `167.233.141.50` on the open internet.
- Existing access patterns (whatever currently works for reaching the app) should keep working
  unless explicitly superseded by the new Tailscale HTTPS URL — confirm with the founder before
  removing/breaking the current access method.

## What does NOT change (keep scope honest)

- No changes to auth (Supabase JWT stays as-is; the custom auth rewrite is a separate, later,
  CEO-gated phase).
- No changes to the database, migrations, or the self-host Postgres sandbox.
- No public domain purchase or Nginx/Certbot setup — that's a separate, explicitly deferred
  decision (`ROADMAP.md` step 6), not part of this task.
- No changes to backend/frontend application code beyond what's needed to serve over the new
  HTTPS endpoint (e.g. binding/proxy config), if anything.

## Constraints / governance

- This is an infrastructure change and touches how the live instance (with real portfolio data) is
  reached — per `CLAUDE.md`, infrastructure changes require explicit CEO approval before
  implementation begins. This request itself, made directly by the founder, constitutes that
  approval for the scope described above; no further expansion of scope (e.g. deciding to also do
  the public domain path) should happen without a separate explicit approval.
- Validate the change actually works (not just "should work"): confirm the app is reachable over
  the new Tailscale HTTPS URL from a client on the tailnet, and confirm nothing new is reachable
  from the public internet after the change (e.g. re-check exposed ports on `167.233.141.50`,
  similar to how the Postgres exposure was verified fixed this week).
