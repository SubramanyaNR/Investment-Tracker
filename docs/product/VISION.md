# Product Vision

> Not loaded into the AI context by default. Read when working on product/positioning, not routine coding.

## What this is and why it exists

A **personal investment portfolio tracker** for a single Indian retail investor holding assets across multiple platforms and classes — crypto on exchanges, mutual funds on Groww/Kuvera, fixed deposits, recurring deposits, PPF, and savings accounts.

**Problem:** No single platform tracks all of these together. The investor had to reconcile across 4-5 apps and a spreadsheet to understand true net worth, P&L, and allocation. This app unifies everything into one dashboard with live prices.

**Direction:** WealthSignal is an **open-source, self-hosted, single-user project** (MIT license) — not a hosted SaaS. The founder runs their own instance; anyone else who wants one runs their own too. See `.ai-sdlc/artifacts/architecture-002/` for the pivot's decision record and `docs/product/ROADMAP.md` for current build status.

## Vision

A beautifully simple, privacy-respecting investment tracker for Indian retail investors who hold assets across multiple platforms. Not another broker app. Not another fintech with an agenda. Not a hosted service holding your financial data — self-hosted, so your portfolio data never leaves infrastructure you control. Just honest, unified tracking.

## Target user

An Indian retail investor who holds crypto + mutual funds + at least one fixed income instrument, is frustrated by switching between 4-5 apps, and is comfortable (or willing to become comfortable) running a small self-hosted app via Docker Compose rather than trusting a third party with brokerage-level financial data.

## Distribution

Open source on GitHub. No pricing, no trial, no billing integration, no growth funnel — value comes from the project being useful and self-hostable, not from a conversion strategy. Community adoption (if any) happens organically through people finding and running the repo.

## External services reference

| Service | Purpose | Tier | Limit |
|---|---|---|---|
| CoinGecko API | Crypto prices, top coins | Free (Demo) | 30 req/min |
| MFAPI (mfapi.in) | MF NAV, scheme search | Free | No documented limit |
| Google Gemini | AI portfolio insights | Free tier | Generous for low usage |
