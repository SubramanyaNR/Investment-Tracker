# Database Schema (complete)

All FK relationships to `assets` have **CASCADE DELETE** — deleting an asset cleans up all related records. UUID PKs everywhere; `Numeric` (never Float) for money.

```
assets                          — master record for every investment
  id (UUID PK)
  name (String)                 — user-defined label
  asset_type (String)           — CRYPTO | MUTUAL_FUND | FD | RD | PPF | SAVINGS_ACC
  category (String)             — crypto | equity | debt | savings
  liquidity_tier (String)       — LIQUID | LOCKED
  created_at (DateTime TZ)

crypto_holdings                 — 1:1 with assets (asset_type=CRYPTO)
  asset_id (UUID PK FK→assets)
  coingecko_id (String)         — e.g. "bitcoin", "ethereum"
  symbol (String)               — e.g. "BTC"
  quantity (Numeric 24,10)
  avg_buy_price (Numeric 18,6)  — INR, weighted average across buys

mutual_fund_holdings            — 1:1 with assets (asset_type=MUTUAL_FUND)
  asset_id (UUID PK FK→assets)
  scheme_code (String)          — MFAPI scheme code
  units (Numeric 24,10)         — calculated: amount_invested / nav_at_purchase
  nav_at_purchase (Numeric 18,6)— weighted average NAV
  monthly_sip (Numeric 18,2)    — nullable; if set, auto-invested on 1st of month

fixed_income_holdings           — 1:1 with assets (FD|RD|PPF|SAVINGS_ACC)
  asset_id (UUID PK FK→assets)
  principal (Numeric 18,2)      — for RD: monthly instalment amount
  annual_rate (Numeric 8,4)     — percentage e.g. 7.1
  start_date (Date)
  maturity_date (Date nullable)
  compounding_frequency (String) — MONTHLY | QUARTERLY | YEARLY

transactions                    — every financial event
  id (UUID PK)
  asset_id (UUID FK→assets CASCADE)
  transaction_type (String)     — BUY | SELL | DEPOSIT
  transaction_date (Date)
  amount (Numeric 18,2)
  units (Numeric 24,8 nullable)
  price_per_unit (Numeric 18,6 nullable)

valuation_history               — daily snapshot per asset
  id (UUID PK)
  asset_id (UUID FK→assets CASCADE)
  valuation_date (Date)
  invested_amount (Numeric 18,2)
  current_value (Numeric 18,2)
  pnl (Numeric 18,2)
  source (String)               — coingecko | mfapi | compound_interest | initial

portfolio_snapshots             — daily portfolio-level rollup (UNIQUE per date)
  id (UUID PK)
  snapshot_date (Date UNIQUE)
  total_invested (Numeric 18,2)
  total_value (Numeric 18,2)
  total_pnl (Numeric 18,2)
  allocation (JSON)
  liquidity (JSON)
  metrics (JSON)

ai_insights                     — stored AI analysis results
  id (UUID PK)
  insight_date (Date)
  observations (JSON)           — [{category, severity, title, message}]
  model (String)                — "gemini" | "rules"
```
