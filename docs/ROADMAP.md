# Roadmap

> Not loaded into the AI context by default. Read when planning what to build next.

## Current state (as of June 2026)

### Done and working
- Full asset management: add, view, delete across all types
- Crypto: live prices via CoinGecko, P&L
- Mutual fund: live NAV via MFAPI, auto-SIP on 1st of month
- Fixed income: compound interest (FD, RD, PPF, Savings)
- Dashboard KPIs, net worth chart, allocation/liquidity donut charts
- Transaction history (buys, sells, deposits)
- AI insights (Gemini 2.0 Flash + rule-based fallback)
- Dark/light theme persisted in localStorage
- Sell crypto / redeem MF (partial) / top-up savings/PPF
- Auto-populate MF NAV on fund select
- Alembic migrations, Docker Compose stack, pg_dump backup script

### Not yet built
- Auth + multi-tenancy (currently single-user)
- Google OAuth login (Auth.js / NextAuth v5)
- Razorpay payments
- API response caching (CoinGecko rate-limit protection)
- CI/CD (GitHub Actions auto-deploy), staging env
- Automated offsite backups (rclone → Google Drive)
- PWA (manifest + service worker), Play Store via TWA
- Ansible provisioning
- Calculation unit tests
- Monitoring / uptime alerting (UptimeRobot)
- Day-wise P&L charts
- "Last updated" timestamps on prices in the UI

## Next major milestones (in order)

### 1. Auth + Multi-tenancy (current priority — only blocker before launch)
- `users` table; `user_id` FK on `assets`
- All endpoints filter by authenticated user
- Google OAuth via Auth.js (NextAuth v5); sessions in Postgres
- Protect routes behind auth middleware

### 2. API caching
- Cache CoinGecko 60s, MFAPI NAV 5min (in-memory or Redis)
- Without it, concurrent refreshes can hit rate limits

### 3. Production infrastructure
- Hetzner VPS, domain + Certbot SSL
- GitHub Actions CI/CD (push to master → deploy)
- Backup container + rclone to Google Drive
- UptimeRobot monitoring

### 4. PWA + Play Store
- manifest.json + service worker (installable)
- TWA wrapper (Bubblewrap) for Play Store; HTTPS prerequisite (needs #3)

### 5. Payments
- Razorpay (UPI, cards, netbanking); gate features behind subscription; payment webhook

### 6. Test suite
- Unit tests for all calculation logic (P&L, compound interest, MF returns)
- API integration tests with a test database
- Post-deploy smoke test script
