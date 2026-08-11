# Roadmap

> Not loaded into the AI context by default. Read when planning what to build next.

## Direction pivot (2026-07-30)

The founder decided to pivot WealthSignal from a hosted, paid, multi-tenant SaaS to an
**open-source, self-hosted, single-user project** (MIT license). See
`.ai-sdlc/artifacts/architecture-002/` for the full decision record.

- `architecture-001` (Hetzner VPS cutover for a hosted Supabase-backed SaaS) is **cancelled**,
  superseded by this pivot.
- Supabase (both managed Postgres and Auth) is being dropped entirely — self-hosted Postgres in
  Docker + custom bcrypt/JWT auth built directly into the FastAPI backend.
- Pricing, trial, Razorpay, and multi-tenant SaaS concerns are **out of scope going forward**.
- `docs/product/VISION.md` still describes the old paid-SaaS positioning and needs its own rewrite
  pass — tracked separately, not covered by this update.

## Current state (as of August 2026)

### Done and working
- Full asset management: add, view, delete across all types (Crypto, MF, FD, RD, PPF, Savings, Manual)
- Crypto: live prices via CoinGecko, P&L, sell flow
- Mutual fund: live NAV via MFAPI, auto-SIP on 1st of month, partial redeem
- Fixed income: compound interest (FD, RD, PPF, Savings), top-up flow
- Manual asset tracking: real estate, gold, unlisted shares (cost basis + estimated value)
- Dashboard KPIs, net worth chart, allocation/liquidity donut charts
- Transaction history (buys, sells, deposits); CSV import for history backfill
- AI insights (Gemini 2.0 Flash + rule-based fallback)
- Dark/light theme persisted in localStorage
- Auto-populate MF NAV on fund select
- XIRR — portfolio-level and per-asset annualised return (F5 + F6)
- Performance movers — best/worst performers monthly (F9) + daily (F10)
- Alembic migrations, `pg_dump` backup script
- Automated test suite: 90 tests passing (unit: compound interest, RD, XIRR, ranking; integration:
  performance API, XIRR API, asset merge, CSV import)
- **Self-host pivot Phase 1 (done)** — sandboxed `postgres:16` container
  (`docker-compose.selfhost.yml`), confirmed the existing Alembic chain applies cleanly to vanilla
  Postgres with no Supabase-specific dependency. Isolated from the live app; nothing wired up yet.

### Transitional / being replaced
- **Deploy model** — backend/frontend currently run as manual `nohup` processes on this host, no
  systemd unit, no process supervisor, no nginx/SSL/domain, no CI/CD, no cron backups. This will be
  reworked as part of the self-host packaging phase, not as a hosted-SaaS VPS cutover.

### Remaining known issues / tech debt
- No "last updated" timestamp on prices in the UI
- `api.mfapi.in` unreachable from this VM (egress issue, unrelated to the pivot) — check before
  assuming a code regression on MF search/NAV failures
- `gate.sh` substring-matches "alembic upgrade" in commit messages (low-pri false-positive)
- **RLS removal deleted its own regression coverage** (`test_rls_backstop.py`, `feature-017`,
  2026-08-10) — correct for single-user today, but if this project ever became multi-tenant again,
  nothing would force RLS (or an equivalent) to be reintroduced correctly. Pure app-layer `WHERE
  user_id` filtering is the only thing standing between tenants from here on.
- **Refresh-token rotation doesn't do family-level revocation** (`feature-017`, 2026-08-10) — reuse
  of an already-rotated token is rejected (401), but only that one token is invalidated, not every
  token descended from it. A stolen token used in a race against the legitimate owner silently
  locks out whichever side loses the race, with no alert either way. Acceptable for a single-user
  instance's threat model today; revisit if that changes.
- **Stale Supabase/RLS references in ops docs** (`SECURITY-AUDIT.md`, `DEPLOY.md`,
  `BACKUP-RESTORE.md`, possibly others) — `feature-017` (2026-08-10) removed Supabase and RLS from
  the codebase but deliberately left this broader doc sweep out of scope. These docs describe a
  security model that no longer exists; worth a dedicated pass before anyone reads them as current.
- **`COOKIE_SECURE=false` on a publicly-routable IP** (`feature-017`, 2026-08-10) — session cookies
  (the entire auth boundary now, not one of two as when Supabase also existed) travel in plaintext
  over `http://167.233.141.50:3000`, the O5-decided default-open self-host path. Not a new exposure
  mechanism (the prior Supabase Bearer token traveled the same plaintext path), but the blast
  radius of a successful interception is higher now — a stolen cookie is a full replayable session,
  not a per-call token. Founder-accepted for now per the O5 decision; revisit if/when that's
  reopened.

---

## Next major milestones (in order)

*Renumbered 2026-08-06 into one flat sequence — each step below is its own gate, not a bundle.
This VM (`167.233.141.50`, on Hetzner) is confirmed as the founder's actual live instance, not just
a build/reference box, which is why operational hardening (1–4) now leads. Triggered by a real
incident this week: BSI/CERT-Bund flagged the self-host sandbox Postgres container publicly
exposed on `0.0.0.0:5432`, fixed same day by rebinding to `127.0.0.1`. See `FEATURE-BACKLOG.md`
`O1`–`O4` for the same items tracked with IDs.*

### 1. Backups + offsite copy  ← current priority
No automated backups exist today (no cron, no offsite copy). Real portfolio data lives on Supabase
free tier, which has no auto-backup either. Highest-severity item on this whole list: the only one
where the failure mode is irreversible data loss. Wire up `backup.sh` on a cron schedule + offsite
copy (rclone → Google Drive, per existing plan).

### 2. Host firewall
`ufw` is currently inactive; only Docker's own iptables rules gate inbound traffic. Enable
default-deny with explicit allows (SSH, app port) so a misconfigured `docker-compose` port mapping
can't silently expose a service again, the way it did this week.

### 3. Process supervision
Backend (`uvicorn`) and frontend (`next start`) currently run as bare `nohup` processes with no
systemd unit; a reboot leaves the app down with no auto-restart. Add systemd units for both.

### 4. Tailscale for private HTTPS access — ✅ done 2026-08-10
Real, trusted HTTPS for personal access (VM + founder's phone, both joined to the tailnet), with
nothing new exposed to the public internet. Implemented via `tailscale serve --bg
http://localhost:3000` — not raw `tailscale cert` as originally scoped; Tailscale's CLI syntax
changed, and `serve` auto-renews the cert and auto-scopes to tailnet-only by construction (a bare
`tailscale cert` cert expires ~90 days with no renewal unless something else serves it). Live at
the founder's `*.ts.net` hostname; `tailscale funnel status` confirmed off (not publicly exposed).
Landed before step 5 (auth rewrite) as planned, so httpOnly/`Secure` cookies and CSRF get
built/tested against real TLS from the start.

**Existing plaintext port 3000 deliberately left open, not closed** — see step 8's out-of-the-box
requirement below. Founder will close it on *this specific instance* only after the OSS GitHub
release, once forked/other self-host instances no longer depend on this repo's default config to
work out of the box.

### 5. Auth rewrite — architecture-002 Phase 2 — ✅ done 2026-08-10
Replaced Supabase Auth with custom auth against self-hosted Postgres (`feature-017`). Delivered
exactly as CEO-decided (2026-07-30):
- HS256 JWT with a generated secret in `.env`
- httpOnly cookie token storage, CSRF protection (double-submit cookie on state-changing requests)
- Short-lived access token + server-tracked, revocable refresh token, rotated on every use
  (logout/password-change revocation)
- First-run bootstrap via `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars — no signup flow, no setup wizard
- No email/SMTP password reset — admin resets via direct DB edit, see
  `docs/runbooks/ADMIN-ACCOUNT-RECOVERY.md`
- RLS policies removed entirely, across all 10 tables that ever had one (single fixed user, no
  longer needed)
- **Test coverage delivered as a completion condition, not deferred**: 211 automated tests (unit +
  integration against a real Postgres) + 15 live adversarial checks + real-browser e2e, covering
  login, token expiry/refresh, revocation, bootstrap idempotency, ownership checks, CSRF, and
  rejection of the old Supabase-style token.

Implemented directly by Claude (not the assigned Gemini/Qwen pipeline — both hit unrelated tooling
failures, founder-directed fallback; see `.ai-sdlc/artifacts/feature-017/`). One accepted, explicit
open item: `COOKIE_SECURE=false` means session cookies travel in plaintext over the public IP path
(`167.233.141.50:3000`) — consequence of the O5 out-of-the-box decision, not an oversight, logged
in the tech-debt section above.

### 6. Domain + HTTPS reassessment (formerly V2)
Not cancelled — reconsidered 2026-08-06. The founder is keeping this Hetzner box as their live
personal instance and wants HTTPS for it; step 4 (Tailscale) may already satisfy that. Once
Tailscale is in place, explicitly decide whether a public domain + Nginx + Certbot is still needed
(e.g. to share access beyond the founder) or whether Tailscale-only access is sufficient for a
single-user deployment. Only build the Nginx/Certbot path if the answer is yes.

### 7. Data migration — architecture-002 Phase 3 — ❌ not done, superseded 2026-08-10
Originally scoped to move the founder's real Supabase portfolio data onto the self-hosted Postgres,
gated on a pre-migration backup + verified restore + rollback point. **The founder explicitly
decided against this** during `feature-017`: "I don't care about any existing user data" — the
gate (no backup yet exists, `O1`/`feature-016` still in planning) became moot rather than satisfied.
The self-hosted Postgres started fresh with an empty schema instead. The old Supabase project's
data is untouched, still sitting there, abandoned rather than migrated or deleted — available later
if anyone ever wants to look at it, but nothing depends on it anymore.

### 8. Self-host packaging & onboarding docs
- Merge/replace `docker-compose.yml` with the self-host Postgres service for a one-command
  `docker-compose up` experience
- README / setup guide for a self-hoster (someone technical enough to clone a repo and run
  docker-compose, not a public SaaS audience)
- License file (MIT, per CEO decision)
- **Out-of-the-box access requirement (decided 2026-08-10):** the app must be reachable over plain
  `localhost`/LAN with zero required setup beyond `docker-compose up` — no Tailscale, nginx, or TLS
  config as a prerequisite to a working install. This is why port 3000 stays open by default (see
  step 4's note); forked/self-hosted instances decide their own exposure/hardening independently of
  what the founder does on their own personal instance.

### 9. VISION.md rewrite
Explicit, CEO-reviewed deliverable — reposition from "₹99/mo paid SaaS, 8-crore TAM" to
open-source/self-hosted/single-user. Not to be silently edited.

### 10. Test suite completion
- Integration tests for `recalculate_crypto_valuations()` and `recalculate_mf_valuations()`
  (live-price paths require mocking CoinGecko/MFAPI)
- Post-deploy smoke test script for self-hosters

### 11. UX / analytics polish (post-release)
- Day-wise P&L chart (sparkline per asset, last 30 days)
- "Last updated" timestamps on crypto and MF prices in the UI
- Pagination / infinite scroll for transaction history (currently fetches all)

---

## Dropped — superseded by the pivot, no longer planned

- Hosted-SaaS production infrastructure: GitHub Actions CI/CD, UptimeRobot monitoring, Ansible
  provisioning, staging environment (`architecture-001`, cancelled) — these assumed serving many
  hosted-SaaS users, not a personal instance
- Google OAuth login — no multi-tenant signup flow in the new single-user model
- PWA + Play Store / TWA submission — not a public-distribution app anymore
- Payments — Razorpay, subscription tiers, payment webhooks
