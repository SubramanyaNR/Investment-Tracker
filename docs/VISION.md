# Product Vision

> Not loaded into the AI context by default. Read when working on product/positioning, not routine coding.

## What this is and why it exists

A **personal investment portfolio tracker** for a single Indian retail investor holding assets across multiple platforms and classes — crypto on exchanges, mutual funds on Groww/Kuvera, fixed deposits, recurring deposits, PPF, and savings accounts.

**Problem:** No single platform tracks all of these together. The investor had to reconcile across 4-5 apps and a spreadsheet to understand true net worth, P&L, and allocation. This app unifies everything into one dashboard with live prices.

**Eventual goal:** Launch as a paid SaaS at ₹99/month for Indian retail investors with the same multi-platform problem. Target market ~8 crore active retail investors in India.

## Vision

A beautifully simple, privacy-respecting investment tracker for Indian retail investors who hold assets across multiple platforms. Not another broker app. Not another fintech with an agenda. Just honest, unified tracking.

## Pricing model
- 21-day free trial (no credit card required)
- ₹99/month or ₹999/year
- Early bird pricing for first 100 users (locks in forever)
- Single plan, no free tier complexity at launch

## Target user
Indian retail investor, 25-40, holds crypto + mutual funds + at least one fixed income instrument, frustrated by switching between 4-5 apps, willing to pay ₹99 for a unified view.

## Hosting plan
- Hetzner CX21 VPS (~$5/month) for up to ~10,000 users
- Docker Compose (no Kubernetes needed at this scale)
- Domain + Nginx + Certbot (HTTPS)
- Backup container + rclone to Google Drive
- UptimeRobot for monitoring

## Distribution strategy (0 → 100 users)
- r/IndiaInvestments, r/IndianStockMarket (organic posts)
- Finance Twitter/X — build in public
- Product Hunt launch
- Telegram finance channels (sponsored posts ₹500-2000/channel)
- No paid ads until conversion is proven

## Scale reference
- 100 users → ₹9,900/month revenue, ~₹690/month costs → net ~₹9,200/month
- 1000 users → ~₹99,000/month revenue, same $9 server cost
- CoinGecko free tier sufficient at any user count with 60-second caching

## External services reference

| Service | Purpose | Tier | Limit |
|---|---|---|---|
| CoinGecko API | Crypto prices, top coins | Free (Demo) | 30 req/min |
| MFAPI (mfapi.in) | MF NAV, scheme search | Free | No documented limit |
| Google Gemini | AI portfolio insights | Free tier | Generous for low usage |
| Razorpay | Payments (not yet integrated) | Pay per transaction | 2% per transaction |
| Hetzner CX21 | VPS hosting (planned) | $5/month | 2 vCPU, 4GB RAM, 20TB traffic |
| Cloudflare Registrar | Domain (planned) | ~$10/year | - |
| Google Drive + rclone | Offsite backups (planned) | Free 15GB | - |
| UptimeRobot | Uptime monitoring (planned) | Free | 50 monitors |
