# Roadmap

> Not loaded into the AI context by default. Read when planning what to build next.

## Current state (as of June 2026)

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
- **Auth + multi-tenancy** — Supabase JWT, per-user data isolation, RLS backstop (M2 resolved)
- **API response caching** — CoinGecko 60 s, MFAPI NAV 5 min (in-memory)
- **XIRR** — portfolio-level and per-asset annualised return (F5 + F6)
- **Performance movers** — best/worst performers monthly (F9) + daily (F10), with Today/Month toggle; `price_per_unit` column ensures capital additions don't inflate the % change
- Alembic migrations, Docker Compose stack, pg_dump backup script

### Remaining known issues / tech debt
- No automated tests for financial calculations (P&L, compound interest, XIRR, MF returns) — high risk with real money
- No "last updated" timestamp on prices in the UI (deferred post-VPS)
- Token revocation (M4) — accepted limitation on Free plan; revisit on Pro/VPS
- Google OAuth disabled — waiting on real domain (provider not enabled in Supabase)
- gate.sh substring-matches "alembic upgrade" in commit messages (low-pri false-positive)

---

## Next major milestones (in order)

### 1. Production infrastructure  ← current priority
The only hard blocker before launch. Auth is done; the app is ready to serve real users.

- Hetzner CX21 VPS (~$5/month), domain + Certbot SSL
- GitHub Actions CI/CD: push to master → deploy
- Backup container + rclone to Google Drive (automated offsite)
- UptimeRobot monitoring + uptime alerting
- Ansible provisioning for repeatable deploys
- Staging environment

### 2. Google OAuth login
Requires a real domain (HTTPS). Supabase provider can be enabled once the VPS + SSL is live.

- Enable Google provider in Supabase dashboard
- Frontend sign-in button; no NextAuth needed (Supabase handles the flow)

### 3. PWA + Play Store
Requires HTTPS (depends on #1).

- `manifest.json` + service worker (installable on Android/iOS)
- TWA wrapper (Bubblewrap) for Play Store submission

### 4. Payments — Razorpay
- UPI, cards, netbanking
- Gate features behind subscription tier
- Payment webhook → user plan stored in DB

### 5. Test suite
Zero automated coverage on financial logic is a launch risk.

- Unit tests: P&L, compound interest (FD/RD/PPF), XIRR, MF return, `price_per_unit` backfill logic
- API integration tests with a test database (pattern established in Stage 3/5 tests)
- Post-deploy smoke test script

### 6. UX / analytics polish (post-launch)
- Day-wise P&L chart (sparkline per asset, last 30 days)
- "Last updated" timestamps on crypto and MF prices in the UI
- Pagination / infinite scroll for transaction history (currently fetches all)
