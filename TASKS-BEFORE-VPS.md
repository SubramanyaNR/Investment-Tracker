# Tasks Before VPS Launch

**Current Status (as of 2026-06-12):**
- ✅ Phase 0 (hardening): Complete
- ✅ Stage 1-3 (features): Complete & on master
- 🔵 Stage 5 (engagement): Ready to merge (feature/stage5-performance branch)
- ❌ VPS: Not started — hard blocker for everything after

---

## 🎯 IMMEDIATE — Pick Up These Before VPS

### 1. **Merge Stage 5** (Ready now)
**Priority:** CRITICAL  
**Owner:** Engineer  
**Est. time:** 2-4 hours (review + test + merge)  
**What:** Merge `feature/stage5-performance` to master
- Best/worst performer (monthly + daily movers)
- Time-range selector (1W/1M/1Y/ALL)
- Monochrome theme option A
- Includes bonus time-range selector on net worth chart

**Acceptance criteria:**
- Branch reviewed & approved
- e2e tests pass on merged code
- No performance regressions
- Feature validated in browser (run app, toggle daily/monthly, check charts render)

**Blocker:** None. Ship this now.

---

### 2. **Automated Test Suite for Auth/Multi-Tenancy** (Recommended by security audit)
**Priority:** HIGH  
**Owner:** Engineer  
**Est. time:** 1.5–2 days  
**What:** Turn the validation matrices from SECURITY-AUDIT.md (Section 7) into committed tests
- Auth matrix: valid/expired/wrong-aud/wrong-iss/missing-sub/missing-exp/non-uuid-sub/alg attacks/tampered/unknown-kid/malformed headers (12 cases)
- Authorization matrix: 401 on all endpoints without token, cross-user 404 on delete/sell/redeem (15 endpoint cases)
- Multi-tenancy matrix: two-user isolation on dashboards/assets/transactions/valuations (4 paths)
- Abuse matrix (new): rate-limit behavior, oversized payloads, repeated unknown-kid (TODO — starts here)

**Current status:** Verified by one-off scripts during audit (June 3), not yet in CI.

**Acceptance criteria:**
- Tests in `tests/` directory
- All 31+ test cases passing
- CI runs them on every PR
- Coverage reports show auth paths at 90%+

**Why:** Zero critical/high auth bugs found, but no automated checks — future query changes could break isolation. This is your backstop.

---

### 3. **Mobile Responsiveness Audit** (Can start now, P3)
**Priority:** HIGH  
**Owner:** Designer/QA  
**Est. time:** 3–4 days  
**Target:** 390px (mobile-first requirement)  
**What:** Audit all screens at breakpoints: 390px, 480px, 768px, 1024px+

**Screens to check:**
- Dashboard (KPIs, charts, movers)
- Holdings list
- Add asset flow
- Transaction history (paginated)
- Crypto sell flow
- MF redeem flow
- Settings/theme toggle
- Onboarding (once built)

**Acceptance criteria:**
- No horizontal scroll at 390px
- All buttons/inputs touch-friendly (48px min)
- Charts readable on mobile
- Navigation/sidebar collapses correctly
- Screenshot evidence for each screen + breakpoint

**Blocker:** None. Start now.

**Note:** P3 in backlog is "do before first paying user" but doable pre-VPS. You'll catch responsive bugs before launch.

---

### 4. **Onboarding / First-Run Experience** (Can start now, P2)
**Priority:** HIGH  
**Owner:** Designer + Engineer  
**Est. time:** 5–7 days  
**What:** Empty dashboard killer fix

Current flow: User signs up → blank dashboard → confused  
Desired flow: User signs up → "Add your first asset" prompt → guided first asset entry → dashboard populates

**Scope:**
- Detect first-time user (no assets yet)
- Show **one-time** onboarding overlay/modal:
  - "Welcome to WealthSignal"
  - "Add your first investment to get started"
  - Button → launch add-asset modal
- After first asset added, overlay gone forever
- Optional: Show next steps (CSV import, XIRR explanation)

**Acceptance criteria:**
- First-run flow validated in browser (new user, no assets)
- Overlay appears once, never again
- Add-asset modal launches from overlay
- Asset appears on dashboard after submit
- Existing users unaffected (no regression)

**Blocker:** None. High conversion impact — do this.

---

### 5. **Data Export (CSV)** (Can start now, P4)
**Priority:** MEDIUM  
**Owner:** Engineer  
**Est. time:** 2–3 days  
**What:** Let users download their data (trust signal, legal requirement coming)

**Exports:**
- Holdings (current state): asset name / type / quantity / price_per_unit / valuation / currency
- Transactions (full history): date / asset / type (BUY/SELL/DEPOSIT/WITHDRAW) / amount / units / price_per_unit

**Endpoints:**
- `GET /export/holdings.csv` — current portfolio
- `GET /export/transactions.csv` — all transactions

**Acceptance criteria:**
- Endpoints return valid CSV (proper quoting, escaping)
- User can only download own data (auth enforced)
- Data matches what they see in UI
- File downloads in browser without errors
- Frontend has "Export Data" button on settings/account page

**Blocker:** None.

---

### 6. **Terms of Service + Privacy Policy** (Can start now, P5)
**Priority:** MEDIUM  
**Owner:** Legal/Founder  
**Est. time:** 1–2 days  
**What:** Required before taking payment

**ToS:** Standard SaaS template
- Paid subscription terms (₹99/mo, ₹999/yr, 21-day free trial)
- Refund policy (if any)
- Account termination
- Liability limits

**Privacy Policy:** Plain-English version (key trust signal)
- What data is collected (assets, transactions, valuations)
- Why (portfolio tracking, insights)
- How it's stored (Supabase, encrypted at rest & in transit)
- Your rights (export, delete)
- Data retention (per account deletion)
- Third-party services (CoinGecko, MFAPI, Gemini — read-only)
- No selling data, no tracking pixels

**Acceptance criteria:**
- Policies posted on frontend (separate pages, linked in footer)
- Plain language, <5min read for Privacy Policy
- Links work on all devices
- Accept-on-signup flow ready (not wired up yet, just docs)

**Blocker:** None, but required before Razorpay integration.

---

### 7. **End-to-End Manual Test Suite** (QA work, can start now)
**Priority:** MEDIUM  
**Owner:** QA  
**Est. time:** 2–3 days  
**What:** Golden path + edge cases, before VPS

**Golden Path (happy path):**
1. Sign up with new email → email confirmation → redirect to dashboard
2. Add first crypto (BTC) → live price fetches → appears in holdings
3. Add MF (growth fund) → NAV auto-populates → appears in holdings
4. Add FD (₹50k) → input maturity date → compound calc shows future value
5. View dashboard → all KPIs populate → XIRR shows 14.3% (or actual %)
6. View net worth chart → line visible with 1W/1M/1Y/ALL toggles
7. View movers → best/worst performers list → toggle Month/Today → changes update
8. Sell crypto → sell 0.5 BTC → P&L updates → transactions show
9. Redeem MF → redeem 10 units → holding updates, cash appears
10. CSV import → upload sample → history backfills → XIRR recalculates
11. Sign out → sign back in → data persists
12. Delete account → all data purged

**Edge Cases:**
- Add duplicate asset (scheme_code / coingecko_id) → merge or error?
- Sell more than you own → error?
- Top-up on nonexistent FD → error?
- Offline → offline handling?
- Rapid API calls → rate limiting works?
- Switch theme dark/light → persists?
- Mobile 390px → responsive?

**Acceptance criteria:**
- Test plan documented (checklist)
- All golden path steps pass
- Edge cases handled gracefully (error msgs, no crashes)
- No console errors
- Performance acceptable (<2s API calls)
- Screenshots of major screens

**Blocker:** None. Do this to catch bugs before VPS.

---

## 🚀 VPS (Hard Blocker)

Once VPS is live, these unlock:

| Task | Blocker | Estimate |
|---|---|---|
| V1 | Provision Hetzner CX21 | 1–2 hrs |
| V2 | Domain + SSL + Nginx | 2–3 hrs |
| V3 | Deploy stack (alembic + make validate) | 1–2 hrs |
| V4 | Supabase cutover (Site URL, Redirect, CORS, OAuth enable) | 1 hr |
| V5 | Automated backups (rclone → Google Drive) | 1–2 hrs |
| V6 | UptimeRobot monitoring | 30 min |
| V7 | GitHub Actions CI/CD | 2–3 hrs |
| **Total** | | **~1–1.5 days** |

---

## 📋 Post-VPS Launch Readiness (P1–P5)

These unlock **after V2** (domain + SSL):

| ID | Task | Est. | Status |
|---|---|---|---|
| P1 | Google OAuth ("Sign in with Google") | 2 hrs | Blocked on V2 |
| P2 | Onboarding | 5–7 days | **Can start pre-VPS** (do now!) |
| P3 | Mobile audit | 3–4 days | **Can start pre-VPS** (do now!) |
| P4 | Data export (CSV) | 2–3 days | **Can start pre-VPS** (do now!) |
| P5 | ToS + Privacy Policy | 1–2 days | **Can start pre-VPS** (do now!) |

---

## 🟡 Stage 4 (Skipped, Deferred Post-VPS)

CEO decision (2026-06-08): Jump from Stage 3 to Stage 5, skip Stage 4 (risk awareness) until after launch.

| ID | Task | Est. | Why deferred |
|---|---|---|---|
| F7 | Concentration alerts (asset > 40%) | 3–4 days | Engagement (Stage 5) is higher priority pre-VPS |
| F8 | Liquidity analysis (locked vs liquid) | 3–4 days | Engagement (Stage 5) is higher priority pre-VPS |

Resume post-launch if traction exists.

---

## 📊 Pre-VPS Work Summary

| Task | Owner | Est. | Status | Pick this up? |
|---|---|---|---|---|
| 1. Merge Stage 5 | Engineer | 2–4 hrs | Ready | **YES** |
| 2. Auth test suite | Engineer | 1.5–2 days | Recommended | **YES** |
| 3. Mobile audit | QA | 3–4 days | Can start | **YES** |
| 4. Onboarding flow | Designer + Eng | 5–7 days | Can start | **YES** |
| 5. Data export | Engineer | 2–3 days | Can start | **YES** |
| 6. ToS/Privacy | Legal/Founder | 1–2 days | Can start | **YES** |
| 7. E2E test suite | QA | 2–3 days | Can start | **YES** |

**Total pre-VPS work:** ~3–4 weeks of focused effort  
**Benefit:** Merged codebase, tested auth, mobile-ready, compliant, trustworthy for day 1

---

## ⛔ Explicitly Blocked on VPS

- ❌ Google OAuth (needs domain)
- ❌ PWA / Play Store (needs HTTPS)
- ❌ Payments (Razorpay, needs production infra)
- ❌ Automated backups (needs VPS)
- ❌ CI/CD (needs VPS)
- ❌ Real domain CORS (needs VPS)

All blocked until **V1–V2** complete.

---

## 🎯 Recommended Sequencing

**Week 1:**
- Merge Stage 5 (2–4 hrs)
- Start mobile audit (parallel)
- Start auth test suite (parallel)

**Week 2–3:**
- Finish mobile audit (3–4 days)
- Finish auth tests (1.5–2 days)
- Start onboarding UX/design
- Start data export backend

**Week 3–4:**
- Finish onboarding (5–7 days)
- Finish data export (2–3 days)
- Write ToS/Privacy (1–2 days)
- E2E test suite (2–3 days, final week)

**End of Week 4:** Deploy to staging, run E2E tests, fix bugs, **then** start VPS work.

---

## 🔗 Decision Gates

**Before merging Stage 5 → master:**
- Code review ✅
- e2e tests pass ✅
- No regressions on existing features ✅

**Before starting VPS work:**
- All P1–P5 launch-readiness tasks done (except P1, which needs VPS)
- E2E test suite passing ✅
- Mobile audit complete ✅
- ToS/Privacy ready ✅

**Before first paying user:**
- VPS live + deployed ✅
- Google OAuth working ✅
- Backup routine proven ✅
- UptimeRobot monitoring active ✅
