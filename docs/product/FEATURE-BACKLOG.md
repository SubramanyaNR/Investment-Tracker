# WealthSignal — Feature Backlog

> Master reference for all feature work: completed, in-progress, planned, on hold, and cancelled.
> Updated: 2026-06-07. Load this file when planning what to build next.

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
| A1 | Docker/env alignment with RLS/Supabase architecture | ✅ | `a8a409b` | |
| A2 | Frontend API routing fix (`/api` proxy, not `localhost:8000`) | ✅ | `c5813a9` | |
| A3a | Unit test suite (auth verifier, financial calcs, cache, rate limit) | ✅ | `05d41b8` | |
| A3b | Integration tests (RLS backstop, authz, tenant isolation, concurrency) | ✅ | `39be06f` | |
| A4 | Financial correctness — RD compounding fix, crypto price fault isolation | ✅ | `4736235` | |
| A5 | `/market/*` in-process cache + per-user/per-IP rate limiting | ✅ | `85fab46` | ADR 0004 |
| A6 | Supabase production config checklist, M4 accepted as Free-plan limit | ✅ | `e74a7bf` | `DEPLOY.md` |
| A7 | Automated offsite backups (rclone → Google Drive) | ⏸️ | — | Deferred to VPS day |
| A8 | Structured request/error logging + Alembic model drift guard | ✅ | `c88556e` | |
| A9 | JWKS unknown-kid negative cache (DoS hardening, M2 closed) | ✅ | `22936cd` | |
| A10a | Snapshot atomic upsert via `ON CONFLICT DO UPDATE` (L6 — part 1) | ✅ | `d04a7f0` | |
| A10b | Holding uniqueness constraints + `IntegrityError` race-safe merge (L6 — part 2) | ✅ | `beda9db` | |
| A11 | Transaction pagination (`limit`/`offset`, envelope response) + L6 doc closure | ✅ | `b9f71a1` | |

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
| C16 | Supabase auth (ES256 JWT), PKCE flow, email confirmation | ✅ | |
| C17 | RLS + `app_user` least-privilege role + per-request GUC | ✅ | |
| C18 | `DELETE /account` — full data purge | ✅ | |

---

## Pre-VPS Feature Stages
*~7 weeks of focused work. Easy wins first.*

---

### Stage 1 — Quick Wins
*Target: Week 1. No dependencies. Immediate visible improvement.*

| ID | Feature | Est. Effort | Status | Priority rationale |
|---|---|---|---|---|
| F1 | **Net worth timeline — cost basis overlay** | 2 hours | 🟡 | One extra data series on existing chart. `total_invested` already in `portfolio_snapshots`. Makes the P&L story visual. |
| F2 | **Price freshness indicators** | 2 hours | 🟡 | Cache TTL metadata exists. "Prices updated X min ago" label per section. Trust detail, ships invisible. |
| F3 | **Manual asset tracking (simple)** | 2 days | 🟡 | New asset type: name + current value (manual) + optional notes. No API, no XIRR. Closes net worth completeness gap for unlisted shares, smallcase, gold, real estate estimates. |

**Stage 1 output:** Richer dashboard, complete net worth picture, trust detail. Ships in 3 days.

---

### Stage 2 — CSV Transaction Import
*Target: Weeks 2–3. Onboarding multiplier. Ships before XIRR to maximise XIRR's day-1 power.*

| ID | Feature | Est. Effort | Status | Priority rationale |
|---|---|---|---|---|
| F4 | **CSV transaction import** | 1.5–2 weeks | 🟡 | Lets users backfill 3+ years of SIP and crypto history. Without this, XIRR is labelled "since tracking started." With this, XIRR is immediately powerful for all existing portfolio history. |

**Scope (strict):** Transaction import only (not holdings state). Columns: `transaction_date`, `asset_type`, `asset_name`, `transaction_type`, `amount`, `units`, `price_per_unit`, `coingecko_id` (if CRYPTO), `scheme_code` (if MUTUAL_FUND). Downloadable CSV template provided in UI. Row-by-row validation, preview table, confirm before import. Reuses existing asset merge logic.

**Stage 2 output:** Users bring their full portfolio history into WealthSignal at signup. Free trial converts better because the app is immediately useful.

---

### Stage 3 — XIRR
*Target: Weeks 4–5. The headline feature. Justifies ₹99/month.*

| ID | Feature | Est. Effort | Status | Priority rationale |
|---|---|---|---|---|
| F5 | **XIRR — backend calculation** | 1 week | 🟡 | Newton-Raphson solver. Portfolio-level and per-asset. Uses full transaction history from F4. |
| F6 | **XIRR — frontend presentation + SIP performance view** | 1 week | 🟡 | XIRR shown as a KPI card on dashboard (portfolio total). Per-asset XIRR on holdings page. SIP-specific view: total invested / current value / XIRR since first SIP, per MF fund. Labelled "XIRR since [start date]." |

**Notes:** XIRR labelled clearly as "since tracking started" if full history is not available. Edge cases: zero investment, identical buy/sell dates, negative cash flows — all need test coverage.

**Stage 3 output:** "I'm earning 14.3% XIRR on my portfolio." The feature that drives word-of-mouth and makes users stay.

---

### Stage 4 — Risk Awareness
*Target: Week 6. High value, low complexity now that data model is complete.*

| ID | Feature | Est. Effort | Status | Priority rationale |
|---|---|---|---|---|
| F7 | **Concentration alerts** | 3–4 days | 🟡 | Compute % of portfolio in each asset. Warn if any single asset > 40% of total. Surface as a subtle badge or warning on dashboard. Actionable, hard to misinterpret. |
| F8 | **Liquidity analysis** | 3–4 days | 🟡 | Bucket portfolio into liquid / medium / locked using existing `liquidity_tier` and `maturity_date`. Show: "42% of your portfolio is locked for 2+ years, maturing between [dates]." Liquidity ladder view. |

**Stage 4 output:** Turns WealthSignal from a tracker into a tool that proactively surfaces risk. Differentiates from Groww/Kuvera which only show returns.

---

### Stage 5 — Performance Insights
*Target: Week 7. Engagement feature. Monthly variant ships first (no new data needed); daily variant follows.*

| ID | Feature | Est. Effort | Status | Priority rationale |
|---|---|---|---|---|
| F9 | **Best & worst performer — monthly** | 3–4 days | 🟡 | Compare each asset's `valuation_history` (latest this month vs earliest this month) to rank % change. Show top 3 / bottom 3. Data already exists if recalculate is called regularly. |
| F10 | **Best & worst performer — daily** | 3–4 days | 🟡 | Requires daily per-asset valuation storage. Enhance `daily_snapshot_job` scheduler to call recalculate for each user at 23:55 so valuation_history has daily rows. Then compare today vs yesterday per asset. |

**Notes:** Monthly ships first (no scheduler change needed). Daily follows once scheduler enhancement is in place. Both views restricted to assets with live prices (CRYPTO + MUTUAL_FUND); FI assets excluded as they don't have daily price movement.

**Stage 5 output:** A reason to open the app on any given day. Engagement feature that works in volatile markets; labelled "monthly change" and "daily change" to set correct expectations.

---

## VPS Deployment Milestone
*Trigger: VPS provisioned + domain live. Run `docs/runbooks/DEPLOY.md`.*

| ID | Task | Owner | Notes |
|---|---|---|---|
| V1 | Provision Hetzner CX21 (~$5/mo) | Founder | 2 vCPU, 4GB RAM |
| V2 | Domain + Cloudflare + Nginx + Certbot (HTTPS) | Founder | Prerequisite for Google OAuth and PWA |
| V3 | Deploy stack (`alembic upgrade head` → `make dev` → `make validate`) | Engineer | Runbook: `DEPLOY.md` |
| V4 | B1 Supabase cutover — Site URL, Redirect URLs, CORS origin set to real domain | Founder | Enables Google OAuth; fixes L3 |
| V5 | A7 — Automated offsite backups (cron `make backup` → rclone → Google Drive) | Engineer | |
| V6 | UptimeRobot monitoring (free, email alerts) | Founder | 50 monitors free tier |
| V7 | GitHub Actions CI/CD (push to `master` → SSH deploy) | Engineer | |
| V8 | F2 — Price freshness indicators (ships on VPS day, 2 hours) | Engineer | |

---

## Post-VPS Pipeline
*Features that require real domain / HTTPS, or are post-launch priorities.*

### Launch Readiness (do before first paying user)

| ID | Feature | Est. Effort | Status | Notes |
|---|---|---|---|---|
| P1 | **Google OAuth ("Sign in with Google")** | VPS day task | 🟡 | Code handles it; just needs domain in Supabase console |
| P2 | **Onboarding / first-run experience** | 1 week | 🟡 | Empty dashboard is a conversion killer. "Add your first asset" prompt + guided first step. |
| P3 | **Mobile responsiveness audit** | 1 week | 🟡 | Target user is mobile-first. Every screen must work at 390px. |
| P4 | **Data export (CSV)** | 3–4 days | 🟡 | Trust signal: "can I get my data out?" Holdings + transactions export. |
| P5 | **Terms of Service + Privacy Policy** | 1 day writing | 🟡 | Required before taking payment. Plain-English privacy policy is the key trust signal. |

### Growth Features

| ID | Feature | Est. Effort | Status | Notes |
|---|---|---|---|---|
| P6 | **Razorpay payments** | 2–3 weeks | 🟡 | UPI/cards, ₹99/month + ₹999/year, 21-day free trial gating, webhook |
| P7 | **AI monthly email report** | 2–3 weeks | ⏸️ | On hold until other features complete. Needs email provider (Resend/Postmark) + prompt engineering + monthly scheduler. |
| P8 | **Net worth benchmark comparison (Nifty 50)** | 2 weeks | 🟡 | Requires external index data source. Phase 2. |
| P9 | **Notes per asset** | 1 day | 🟡 | Free-text notes field on each holding. Turns tracker into investment journal. |
| P10 | **PWA (manifest + service worker)** | 1 week | 🟡 | Installable. Requires HTTPS (V2). |
| P11 | **Play Store via TWA** | 2–3 weeks | 🟡 | Bubblewrap wrapper. Requires PWA (P10). |
| P12 | **Day-wise P&L charts** | 1–2 weeks | 🟡 | Historical net worth drilldown per asset. |
| P13 | **Manual ESOPs tracking** | 3–4 weeks | 🟡 | Vesting schedules, cliff dates, strike price. Scoped separately from F3 (simple manual). |
| P14 | **Dividend / interest income view** | 1 week | 🟡 | Running total of passive income from portfolio. Separate from capital appreciation. |
| P15 | **Smallcase integration** | 2 weeks | 🟡 | Smallcase has an API. Proper integration, not manual entry. |
| P16 | **Concentration/liquidity alerts — advanced** | 1 week | 🟡 | Expand F7/F8 with user-configurable thresholds post-launch. |
| P17 | **Serve CSV import template via Nginx static asset** | 2 hours | 🟡 | Currently served by FastAPI (GET /import/csv/template). Move to Nginx static file delivery post-VPS to reduce unnecessary FastAPI overhead for a hardcoded file. Prerequisite: V2 (Nginx). No user impact; transparent swap. |

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
COMPLETED (Phase 0)
  A1 A2 A3a A3b A4 A5 A6 A8 A9 A10a A10b A11  ← all on master

PRE-VPS STAGES (~7 weeks)
  Week 1    Stage 1 — Quick Wins
              F1  Net worth cost basis overlay    (2 hrs)
              F2  Price freshness indicators      (2 hrs)
              F3  Manual asset tracking           (2 days)

  Weeks 2–3  Stage 2 — CSV Import
              F4  CSV transaction import          (1.5–2 weeks)

  Weeks 4–5  Stage 3 — XIRR
              F5  XIRR backend                   (1 week)
              F6  XIRR frontend + SIP view        (1 week)

  Week 6     Stage 4 — Risk Awareness
              F7  Concentration alerts            (3–4 days)
              F8  Liquidity analysis              (3–4 days)

  Week 7     Stage 5 — Performance Insights
              F9  Best/worst performer — monthly  (3–4 days)
              F10 Best/worst performer — daily    (3–4 days)

VPS DEPLOYMENT (V1–V8)
  Provision → deploy → Supabase cutover → A7 backups → CI/CD

POST-VPS — LAUNCH READINESS (P1–P5)
  Google OAuth → Onboarding → Mobile audit → Data export → ToS/Privacy

POST-VPS — GROWTH (P6–P16)
  Razorpay → AI report (H3) → Benchmark → Notes → PWA → Play Store → ...

ON HOLD (H1–H4)   Realized P&L, Tax dashboard, AI report, SIP comparison
CANCELLED (X1)    Portfolio health score
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
