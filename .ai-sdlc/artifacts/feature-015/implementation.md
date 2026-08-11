## Implementation — manual, performed by the founder (2026-08-10)

Not routed through the Gemini implementation stage: this task requires interactive Tailscale
account/browser auth and admin-console settings (HTTPS Certificates toggle, tailnet join) that no
model can perform unattended. Per SDLC.md's model-ownership fallback, the founder chose to
"perform manual validation" for this stage.

### What was done

1. **Admin console (founder, browser):** enabled "HTTPS Certificates" for the tailnet under DNS
   settings.
2. **VM joined the tailnet:** installed Tailscale (`curl -fsSL https://tailscale.com/install.sh |
   sh`), `sudo tailscale up`, confirmed via `tailscale status`. Assigned hostname:
   `madhyastha-lab-server.tail40a80c.ts.net`.
3. **Phone joined the same tailnet:** Tailscale mobile app, signed into the same account, for
   private access "only me" from a phone as well as the VM.
4. **Served the app over HTTPS:**
   ```
   sudo tailscale serve --bg http://localhost:3000
   ```
   Note: the originally-scoped `tailscale serve https / http://localhost:3000` syntax has been
   replaced by Tailscale — the CLI now defaults to HTTPS-on-443-at-root and just takes the proxy
   target, with `--bg` to persist beyond the shell session.
5. **Deviation from the original request, decided deliberately:** the request as scoped
   (`request.md`) assumed raw `tailscale cert`; that was superseded by `tailscale serve`, which the
   planning review (`planning.md`) had already recommended as the correct mechanism — auto-renews,
   auto-scopes to tailnet-only, requires zero app code changes. No custom Next.js/Node TLS server
   was built, matching the request's "no app code changes beyond what's needed" constraint.
6. **Existing plaintext port 3000 was deliberately left open**, not closed as the request's Phase
   4 checkpoint required a decision on. Rationale (founder): this repo will ship as an OSS
   self-host project, and a fresh `git clone` + `docker-compose up` must work out-of-the-box with
   no Tailscale/nginx/TLS setup required. Closing 3000 now would break that for every future
   self-hoster, not just harden this one instance. Tracked as a separate backlog item, `O5` in
   `FEATURE-BACKLOG.md`, gated on the OSS GitHub release rather than bundled into this task.

### What was explicitly not done (out of scope, per request.md)

- No nginx / Certbot / manual cert files — considered and explicitly rejected (see conversation);
  `tailscale serve` already handles TLS termination and renewal with less surface area.
- No `tailscale funnel` — confirmed off throughout (see qa.md).
- No changes to Supabase Auth, the database, or app code.
