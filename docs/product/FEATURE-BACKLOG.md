# WealthSignal — Feature Backlog

> Master reference for all feature work: completed, in-progress, planned, on hold, and cancelled.
> Updated: 2026-08-06. Load this file when planning what to build next.

## Direction pivot (2026-07-30)

The founder pivoted WealthSignal from a hosted, paid, multi-tenant SaaS to an **open-source,
self-hosted, single-user project** (`architecture-002`, MIT license). This supersedes the VPS
Deployment Milestone and several Post-VPS Pipeline items below — see the `❌ Cancelled` markers
and notes added throughout, and `docs/product/ROADMAP.md` for the current phased plan (auth
rewrite → data migration → self-host packaging). Items unrelated to the hosting/business model
(e.g. product features like notes-per-asset or Smallcase integration) are unaffected and remain
pending as before.

## Status legend

| Symbol | Meaning |
|---|---|
| ✅ | Done — shipped to master |
| 🔵 | In progress |
| 🟡 | Planned — sequenced and ready to start |
| ⏸️ | On hold — approved but deferred by CEO |
| ❌ | Cancelled — removed from roadmap |

---

## Phase 0 — Security Hardening & Infrastructure
*Branch: `feature/phase0-hardening` → merged to `master` 2026-06-07*
*All 94 tests passing.*

| ID | Feature | Status | Commit | Notes |
|---|---|---|---|---|
| A1 | Docker/env alignment with RLS/Supabase architecture | ✅ | `a8a409b` | Merged to master |
| A2 | Frontend API routing fix (`/api` proxy, not `localhost:8000`) | ✅ | `c5813a9` | Merged to master |
| A3a | Unit test suite (auth verifier, financial calcs, cache, rate limit) | ✅ | `05d41b8` | Merged to master |
| A3b | Integration tests (RLS backstop, authz, tenant isolation, concurrency) | ✅ | `39be06f` | Merged to master |
| A4 | Financial correctness — RD compounding fix, crypto price fault isolation | ✅ | `4736235` | Merged to master |
| A5 | `/market/*` in-process cache + per-user/per-IP rate limiting | ✅ | `85fab46` | Merged to master |
| A6 | Supabase production config checklist, M4 accepted as Free-plan limit | ✅ | `e74a7bf` | Merged to master |
| A7 | Automated offsite backups (rclone → Google Drive) | ⏸️ | — | No longer tied to VPS day (V5, cancelled) — now part of the self-host packaging phase, see `ROADMAP.md` |
| A8 | Structured request/error logging + Alembic model drift guard | ✅ | `c88556e` | Merged to master |
| A9 | JWKS unknown-kid negative cache (DoS hardening, M2 closed) | ✅ | `22936cd` | Merged to master |
| A10a | Snapshot atomic upsert via `ON CONFLICT DO UPDATE` (L6 — part 1) | ✅ | `d04a7f0` | Merged to master |
| A10b | Holding uniqueness constraints + `IntegrityError` race-safe merge (L6 — part 2) | ✅ | `beda9db` | Merged to master |
| A11 | Transaction pagination (`limit`/`offset`, envelope response) + L6 doc closure | ✅ | `b9f71a1` | Merged to master |
| A12 | Transaction date filtering (`from`/`to` inclusive) | ✅ | | Extension of A11 |
| A13 | Holdings pagination (`GET /assets`, envelope response) | ✅ | `d48cd5a`, `a30b33e` | feature-013; fix commit added missing `AssetPage` type |
| A14 | Replace deprecated FastAPI `on_event` with `asynccontextmanager` lifespan | ✅ | `fa9db10` | feature-014 |

---

## Core Product — Already Shipped
*Features working in production prior to Phase 0.*

| ID | Feature | Status | Notes |
|---|---|---|---|
| C1 | Full asset management — add, view, delete (CRYPTO / MF / FD / RD / PPF / SAVINGS_ACC) | ✅ | |
| C2 | Crypto live prices via CoinGecko + P&L | ✅ | |
| C3 | Mutual fund live NAV via MFAPI, auto-SIP on 1st of month | ✅ | |
| C4 | Fixed income compound interest valuation (FD, RD, PPF, Savings) | ✅ | |
| C5 | Dashboard KPIs — net worth, total invested, total P&L, P&L % | ✅ | |
| C6 | Net worth chart (portfolio snapshots over time) | ✅ | |
| C7 | Allocation donut chart (by asset type) | ✅ | |
| C8 | Liquidity donut chart (liquid / medium / locked) | ✅ | |
| C9 | Transaction history view | ✅ | Paginated since A11 |
| C10 | AI insights (Gemini 2.0 Flash + rule-based fallback) | ✅ | |
| C11 | Dark / light theme, persisted in localStorage | ✅ | |
| C12 | Sell crypto (partial) | ✅ | |
| C13 | Redeem mutual fund (partial) | ✅ | |
| C14 | Top-up savings / PPF | ✅ | |
| C15 | Auto-populate MF NAV on fund select | ✅ | |
| C16 | Supabase auth (ES256 JWT), PKCE flow, email confirmation | ✅ | Being replaced — `architecture-002` Phase 2 (custom bcrypt/JWT auth, see `ROADMAP.md`) |
| C17 | RLS + `app_user` least-privilege role + per-request GUC | ✅ | Being removed entirely under Phase 2 (single-user deployment no longer needs RLS) |
| C18 | `DELETE /account` — full data purge | ✅ | |

---

## Pre-VPS Feature Stages
*~7 weeks of focused work. Easy wins first.*

---

### Stage 1 — Quick Wins
*Target: Week 1. No dependencies. Immediate visible improvement.*
*Status: ✅ SHIPPED (merged to master)*

| ID | Feature | Est. Effort | Status | Priority rationale |
|---|---|---|---|---|
| F1 | **Net worth timeline — cost basis overlay** | 2 hours | ✅ | Implemented via `total_invested` in portfolio snapshots |
| F2 | **Price freshness indicators** | 2 hours | ✅ | Dashboard shows "Prices updated X min ago" |
| F3 | **Manual asset tracking (simple)** | 2 days | ✅ | Real estate, gold, unlisted shares support added |

**Stage 1 output:** ✅ COMPLETE — Richer dashboard, complete net worth picture, trust detail.

---

### Stage 2 — CSV Transaction Import
*Target: Weeks 2–3. Onboarding multiplier. Ships before XIRR to maximise XIRR's day-1 power.*
*Status: ✅ SHIPPED (merged to master)*

| ID | Feature | Est. Effort | Status | Priority rationale |
|---|---|---|---|---|
| F4 | **CSV transaction import** | 1.5–2 weeks | ✅ | Full transaction history backfill working. Template downloadable, validation + preview UI implemented. |

**Scope (strict):** ✅ Transaction import only. Columns: `transaction_date`, `asset_type`, `asset_name`, `transaction_type`, `amount`, `units`, `price_per_unit`, `coingecko_id` (CRYPTO), `scheme_code` (MUTUAL_FUND). CSV template served via public endpoint.

**Stage 2 output:** ✅ COMPLETE — Users can backfill 3+ years of portfolio history at signup.

---

### Stage 3 — XIRR
*Target: Weeks 4–5. The headline feature. Justifies ₹99/month.*
*Status: ✅ SHIPPED (merged to master)*

| ID | Feature | Est. Effort | Status | Priority rationale |
|---|---|---|---|---|
| F5 | **XIRR — backend calculation** | 1 week | ✅ | Newton-Raphson solver. Portfolio-level and per-asset. Uses full transaction history. |
| F6 | **XIRR — frontend presentation + SIP performance view** | 1 week | ✅ | XIRR KPI card on dashboard. Per-asset XIRR on holdings. SIP performance view with total invested / current value. |

**Notes:** ✅ XIRR correctly labelled "since tracking started" or with actual start date. Edge cases (zero investment, identical dates, negative flows) handled. 14 Newton-Raphson tests passing.

**Stage 3 output:** ✅ COMPLETE — "I'm earning 14.3% XIRR on my portfolio." The core engagement feature.

---

### Stage 4 — Risk Awareness
*Target: Week 6. High value, low complexity now that data model is complete.*
*Status: ⏸️ SKIPPED (per CEO decision 2026-06-08)*

| ID | Feature | Est. Effort | Status | Priority rationale |
|---|---|---|---|---|
| F7 | **Concentration alerts** | 3–4 days | ⏸️ | Deferred post-VPS. Moving directly to Stage 5 engagement features instead. |
| F8 | **Liquidity analysis** | 3–4 days | ⏸️ | Deferred post-VPS. Moving directly to Stage 5 engagement features instead. |

**Decision:** CEO prioritized engagement (Stage 5) over risk awareness before VPS. These remain in the backlog for post-launch. Can be revisited once VPS is live and user traction exists.

---

### Stage 5 — Performance Insights
*Target: Week 7. Engagement feature. Monthly variant ships first (no new data needed); daily variant follows.*
*Status: ✅ SHIPPED (merged to master 2026-06-12)*

| ID | Feature | Est. Effort | Status | Impl. Notes |
|---|---|---|---|---|
| F9 | **Best & worst performer — monthly** | 3–4 days | ✅ | Shipped. Compares assets' `valuation_history` (latest month vs earliest month). Top 3 / bottom 3. |
| F10 | **Best & worst performer — daily** | 3–4 days | ✅ | Shipped. Daily snapshots working. Today/Month tab switcher implemented. Uses `price_per_unit` to exclude capital additions. |
| Bonus | **Time-range selector (net worth chart)** | — | ✅ | 1W/1M/1Y/ALL selector on net worth chart for better context. |

**Implementation details:**
- Backend: `GET /performance/monthly` + `GET /performance/daily` endpoints
- Database: `price_per_unit` column added to `valuation_history` (handles pre-column rows gracefully)
- Frontend: MoversSection component with Today/Month toggle + NetWorthChart range selector
- Both views restricted to CRYPTO + MUTUAL_FUND (live prices); FI assets excluded (no daily movement)
- Tests: 305 integration + 78 unit tests for performance service; all 171 backend tests passing

**Stage 5 status:** ✅ COMPLETE. 7 commits merged (F9, F10, time-range, graphify infra, docs).

---

## VPS Deployment Milestone — ❌ CANCELLED (superseded 2026-07-30)

This entire milestone assumed a hosted, Supabase-backed, multi-tenant SaaS on a Hetzner VPS
(`architecture-001`). That plan is cancelled — superseded by the OSS self-host pivot
(`architecture-002`). Table kept for historical record; see `docs/product/ROADMAP.md` for what
replaced it (self-host Docker packaging, no domain/CI-CD/Ansible requirement).

| ID | Task | Owner | Status | Notes |
|---|---|---|---|---|
| V1 | Provision Hetzner CX21 (~$5/mo) | Founder | ❌ | Cancelled — no hosted VPS target anymore |
| V2 | Domain + Cloudflare + Nginx + Certbot (HTTPS) | Founder | 🟡 | **Reconsidered 2026-08-06** — founder is keeping this Hetzner box as their live personal instance, wants HTTPS for it. Sequenced behind O4 (Tailscale) below; reassess whether a public domain is even needed once Tailscale is in place. |
| V3 | Deploy stack (`alembic upgrade head` → `make dev` → `make validate`) | Engineer | ❌ | Superseded by self-host `docker-compose up` packaging |
| V4 | B1 Supabase cutover — Site URL, Redirect URLs, CORS origin set to real domain | Founder | ❌ | Moot — Supabase being dropped entirely, not cut over |
| V5 | A7 — Automated offsite backups (cron `make backup` → rclone → Google Drive) | Engineer | 🟡 | Concept carried forward into self-host packaging phase, not VPS-specific anymore |
| V6 | UptimeRobot monitoring (free, email alerts) | Founder | ❌ | Not applicable to a self-hosted single-user install |
| V7 | GitHub Actions CI/CD (push to `master` → SSH deploy) | Engineer | ❌ | No central deploy target to push to anymore |
| V8 | F2 — Price freshness indicators (ships on VPS day, 2 hours) | Engineer | ✅ | Already shipped independent of VPS — dashboard shows "Prices updated X min ago" (see F2) |

---

## Operational Hardening — Personal Instance (added 2026-08-06)
*Triggered by a real incident: BSI/CERT-Bund flagged the self-host sandbox Postgres container
publicly exposed on `0.0.0.0:5432` (fixed same day, rebound to `127.0.0.1`). Confirmed this
Hetzner VM (`167.233.141.50`) is the founder's actual live instance, not just a build box — these
are current priority, ahead of the auth rewrite (Phase 2).*

| ID | Feature | Status | Notes |
|---|---|---|---|
| O1 | **Automated backups + offsite copy** | 🟡 | Local half done 2026-08-10 (`feature-016`) — cron `make backup`, atomic gzipped `pg_dump`, integrity checks, 30-day retention. Offsite copy (rclone → Google Drive) still open, by explicit founder decision to ship local-only first. |
| O2 | **Host firewall (`ufw`, default-deny)** | ✅ | Done 2026-08-13 (`feature-018`) — `ufw` active + `systemctl`-enabled, default-deny incoming, explicit allows for SSH/3000/`tailscale0`, `ufw-docker` installed. Confirmed persists across a real reboot. Docker-recreate regression check + external scan still open, founder to run directly — see `docs/runbooks/FIREWALL.md`. |
| O3 | **Process supervision (systemd units)** | 🟡 | Backend (`uvicorn`) and frontend (`next start`) run as bare `nohup` processes, no auto-restart on reboot. |
| O4 | **Tailscale for private HTTPS access** | ✅ | Done 2026-08-10 — implemented via `tailscale serve --bg http://localhost:3000` (Tailscale's CLI changed; raw `tailscale cert` as originally scoped doesn't auto-renew). Live at founder's `*.ts.net` hostname, reachable from VM + founder's phone (joined to same tailnet); `funnel status` confirmed off, nothing newly public. |
| O5 | **Close plaintext port 3000 (founder's own instance, post-OSS-launch)** | 🟡 | Deliberately deferred, not forgotten. Port 3000 stays open now so a fresh `git clone` + `docker-compose up` works out-of-the-box for self-hosters — no Tailscale/nginx/TLS setup required to get a working install (decided 2026-08-10). After the OSS GitHub release, close 3000 on *this* founder instance specifically (loopback bind + `ufw` rule); personal access continues via the O4 Tailscale URL. Forks/other self-hosters keep the open-by-default behavior and decide their own hardening independently. |
| O6 | **SSH key-based authentication (disable password login)** | 🟡 | VM currently only has password-based SSH login. Not a blocker for O2 (`ufw` filters by port/IP, not auth method) — logged separately as general access hardening. Add a public key, confirm key-based login works, then disable `PasswordAuthentication` in `sshd_config`. Low urgency, cheap to do. |

**Sequencing:** these IDs map onto `docs/product/ROADMAP.md`'s flat numbered milestone list
(renumbered 2026-08-06): O1=step 1, O2=step 2, O3=step 3, O4=step 4, auth rewrite=step 5, V2
domain reassessment=step 6. O1–O3 can happen in any order, cheaply, without blocking anything. O4
must land before step 5 (auth rewrite) — done. V2 is deferred behind O4, reassessed at step 6. O5
is independent of this sequence entirely — it's gated on the OSS GitHub release (step 8), not on
the auth rewrite.

---

## Post-Pivot Pipeline
*Formerly "Post-VPS Pipeline." Renamed 2026-08-06 — most items here no longer depend on a
domain/HTTPS/VPS launch; they depend on the self-host pivot phases instead. See notes per row.*

### Launch Readiness (do before OSS release)

| ID | Feature | Est. Effort | Status | Notes |
|---|---|---|---|---|
| P1 | **Google OAuth ("Sign in with Google")** | — | ❌ | Cancelled — no multi-tenant signup flow in the single-user model (`architecture-002`) |
| P2 | **Onboarding / first-run experience** | 1 week | ✅ | Done — `feature-005`, `docs/features/onboarding-flow.md` |
| P3 | **Mobile responsiveness audit** | 1 week | 🟡 | Still pending, unaffected by the pivot |
| P4 | **Data export (CSV)** | 3–4 days | ✅ | Done — `feature-006`, `dedb487`, `backend/app/api/export.py` |
| P5 | **Terms of Service + Privacy Policy** | 1 day writing | 🟡 | Still pending; reframe as self-hoster-facing disclaimer (data is theirs, they own the deployment) rather than a SaaS ToS — lower urgency than before, no payment to gate |

### Growth Features

| ID | Feature | Est. Effort | Status | Notes |
|---|---|---|---|---|
| P6 | **Razorpay payments** | — | ❌ | Cancelled — no paid tier in the OSS single-user model |
| P7 | **AI monthly email report** | 2–3 weeks | ⏸️ | On hold, unaffected by the pivot. Needs email provider (Resend/Postmark) + prompt engineering + monthly scheduler. |
| P8 | **Net worth benchmark comparison (Nifty 50)** | 2 weeks | 🟡 | Still pending, unaffected by the pivot |
| P9 | **Notes per asset** | 1 day | 🟡 | Still pending, unaffected by the pivot |
| P10 | **PWA (manifest + service worker)** | 1 week | 🟡 | Open question, not decided: no longer tied to a SaaS HTTPS launch, but may still be worth doing for a self-hoster's own mobile install convenience. Needs explicit CEO call, see `ROADMAP.md`. |
| P11 | **Play Store via TWA** | — | ❌ | Cancelled — public app-store distribution doesn't fit a self-hosted single-user OSS project |
| P12 | **Day-wise P&L charts** | 1–2 weeks | 🟡 | Still pending, unaffected by the pivot |
| P13 | **Manual ESOPs tracking** | 3–4 weeks | 🟡 | Still pending, unaffected by the pivot |
| P14 | **Dividend / interest income view** | 1 week | 🟡 | Still pending, unaffected by the pivot |
| P15 | **Smallcase integration** | 2 weeks | 🟡 | Still pending, unaffected by the pivot |
| P16 | **Concentration/liquidity alerts — advanced** | 1 week | 🟡 | Still pending, depends on F7/F8 first |
| P17 | **Serve CSV import template via Nginx static asset** | — | ❌ | Cancelled — no centralized Nginx VPS deploy planned; FastAPI serving the static file is simpler for self-host |

### On Hold — Requires CEO Approval to Resume

| ID | Feature | Status | Reason |
|---|---|---|---|
| H1 | **Realized vs Unrealized P&L** | ⏸️ | On hold. High value but requires correct FIFO cost basis accounting (2 weeks) and is a dependency for H2. Resume when prioritised. |
| H2 | **Tax dashboard / estimated tax liability** | ⏸️ | On hold. Requires H1. High maintenance (changes every budget). Premium tier feature. Legal disclaimer required. |
| H3 | **AI monthly email report** | ⏸️ | On hold until Stages 1–5 and VPS features complete. |
| H4 | **SIP vs lump sum comparison** | ⏸️ | Interesting analysis, low frequency. Resume post-launch when user data exists. |

### Cancelled

| ID | Feature | Status | Reason |
|---|---|---|---|
| X1 | **Portfolio health score (composite)** | ❌ | Cancelled. False precision without user risk profiling. Misleads users. Revisit only after goal-setting and risk profiling flows exist. |
| X2 | **Best & worst performer — driven by external market events** | ❌ | Merged into F9/F10 (internal portfolio comparison only, not market comparison). |

---

## Full Sequence Summary

```
✅ COMPLETED (Phase 0 — merged to master 2026-06-07)
  A1 A2 A3a A3b A4 A5 A6 A8 A9 A10a A10b A11 A13 A14
  (A13, A14 added later — holdings pagination, on_event→lifespan fix)

✅ COMPLETED (PRE-VPS STAGES 1-3 — merged to master)
  Stage 1: F1 F2 F3  (net worth, freshness, manual assets)
  Stage 2: F4        (CSV transaction import)
  Stage 3: F5 F6     (XIRR backend + frontend)

⏸️ SKIPPED (Stage 4 — still pending, unaffected by the pivot)
  F7 F8  (concentration alerts, liquidity analysis)

✅ COMPLETED (Stage 5 — merged to master 2026-06-12)
  F9 F10 (best/worst performer monthly + daily)
  BONUS: Time-range selector (1W/1M/1Y/ALL)
  398fcc1: Merge Stage 5 — best/worst performers + time-range selector

❌ CANCELLED — superseded by the OSS self-host pivot, architecture-002 (2026-07-30)
  VPS Deployment Milestone (V1, V3, V4, V6, V7) — hosted-SaaS infra no longer applies
  P1 Google OAuth, P6 Razorpay, P11 Play Store, P17 Nginx static asset

🔴 CURRENT PRIORITY — Operational Hardening, personal instance (added 2026-08-06)
  O1 Backups, O2 Firewall, O3 Process supervision
  O4 Tailscale HTTPS — ✅ done 2026-08-10
  (V2 public domain reconsidered — sequenced behind O4)

✅ COMPLETED (2026-08-10) — architecture-002 Phase 2 + 3, feature-017
  Step 5 Auth rewrite (custom bcrypt/HS256, RLS removed) + Step 7 Data migration
  (superseded — founder chose fresh start, no Supabase data carried over)

🟡 DEFERRED TO POST-OSS-LAUNCH (added 2026-08-10)
  O5 Close plaintext port 3000 on founder's own instance (gated on step 8 GitHub release,
  not on the auth rewrite)

✅ COMPLETED, previously mismarked as pending in this doc (corrected 2026-08-06)
  P2 Onboarding, P4 Data export CSV, V8 price freshness

🟡 STILL PENDING — unaffected by the pivot
  P3 Mobile audit, P5 ToS/Privacy (reframed for self-hosters), P8 Benchmark,
  P9 Notes per asset, P12 Day-wise P&L, P13 ESOPs, P14 Dividend/interest,
  P15 Smallcase, P16 Advanced alerts, V5/A7 offsite backups (now self-host-phase-owned)

❓ OPEN QUESTION — needs explicit CEO call
  P10 PWA — worth reviving in a smaller, non-SaaS form? (see ROADMAP.md)

⏸️ ON HOLD (H1–H4) — CEO approval required to resume
  Realized P&L, Tax dashboard, AI report, SIP comparison

❌ CANCELLED (X1)
  Portfolio health score
```

---

## Decision log

| Date | Decision | Made by |
|---|---|---|
| 2026-06-07 | Realized/Unrealized P&L — on hold until further notice | CEO |
| 2026-06-07 | Tax dashboard — on hold until further notice | CEO |
| 2026-06-07 | Portfolio health score (composite) — cancelled | CEO |
| 2026-06-07 | AI monthly email report — on hold until Stages 1–5 complete | CEO |
| 2026-06-07 | Best/worst performer — included in Stage 5 (user overrode Tier 3 verdict) | CEO |
| 2026-06-07 | CSV import — added before XIRR to maximise day-1 XIRR value | PM + Engineer + CTO |
| 2026-06-07 | Manual asset: simple version only (name + price) — ESOPs/real estate separate | PM + Engineer |
| 2026-06-08 | Stage 4 (F7 Concentration Alerts + F8 Liquidity Analysis) — skipped, moving directly to Stage 5 | CEO |
| 2026-07-30 | Pivot to open-source, self-hosted, single-user project (MIT license); `architecture-001` (hosted VPS SaaS) cancelled, superseded by `architecture-002` | CEO |
| 2026-07-30 | VPS Deployment Milestone (V1–V4, V6, V7) and P1 Google OAuth, P6 Razorpay, P11 Play Store, P17 Nginx static asset — cancelled as a consequence of the pivot | CEO |
| 2026-08-06 | Reconciled this doc against actual shipped code and git history: corrected P2 (onboarding), P4 (CSV export), V8 (price freshness) from "planned" to "done"; added A13/A14 for previously untracked shipped work | Claude (documentation reconciliation) |
| 2026-08-06 | BSI/CERT-Bund flagged self-host sandbox Postgres publicly exposed on `0.0.0.0:5432`; fixed same day (rebound to `127.0.0.1`) | Founder + Claude (incident response) |
| 2026-08-06 | This Hetzner VM confirmed as the founder's actual live personal instance, not just a build box — reinstates V2 (domain/HTTPS), deprioritized behind new O1–O4 operational hardening items which become current priority ahead of the auth rewrite | Founder |
| 2026-08-06 | Sequencing: Tailscale (O4) before auth rewrite (Phase 2), so cookie/CSRF work is built and tested against real TLS from the start; public domain (V2) reassessed only after Tailscale is in place | Founder |
| 2026-08-10 | O4 Tailscale implemented manually (not via the Gemini/Qwen AI-SDLC pipeline) using `tailscale serve --bg`, not raw `tailscale cert` as originally scoped — Tailscale's CLI syntax changed since the request was written | Founder + Claude |
| 2026-08-10 | Plaintext port 3000 stays open by default, not closed alongside O4 — required for a fresh `docker-compose up` to work out-of-the-box with zero setup for self-hosters. Added O5 to close it on the founder's own instance specifically, gated on the OSS GitHub release rather than on the auth rewrite. Forks decide their own exposure. | Founder |
| 2026-08-10 | feature-015 (Tailscale, O4) approved and marked complete — implementation/QA/audit performed manually by the founder rather than via the Gemini/Qwen pipeline, per SDLC.md's model-ownership fallback for stages requiring interactive account-level access | Founder |
| 2026-08-10 | feature-017 scope resolved through discussion: full cutover now (custom auth + fresh local Postgres), not just "change db" — auth rewrite (`ROADMAP.md` step 5) and data migration (step 7) both folded in, reversing the original sequencing recommendation (auth-before-migration) in favor of doing both together | Founder |
| 2026-08-10 | feature-017: no data migration — founder explicitly disregarded existing Supabase data ("I don't care about any existing user data"). Old Supabase project left untouched, not migrated or deleted. `O1`/backup-gate question became moot rather than satisfied. | Founder |
| 2026-08-10 | feature-017 implementation performed by Claude, not the assigned Gemini (daily quota exhausted) — founder-directed fallback, same pattern as O4 | Founder |
| 2026-08-10 | feature-017 QA performed by Claude, not the assigned Qwen (OpenRouter API key returned "User not found" — looks invalid/revoked, not transient) — founder-directed fallback. Flagged explicitly: no independent model verified this auth-critical code. | Founder |
| 2026-08-10 | feature-017 approved and marked complete — auth rewrite (`ROADMAP.md` step 5) and data-migration decision (step 7) both closed. `COOKIE_SECURE=false` on the public IP and refresh-token family-revocation gap left as explicit, accepted tech debt, not silently resolved. | Founder |
