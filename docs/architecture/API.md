# API Endpoints (complete reference)

```
GET  /health                                      → {status: "ok"}

GET  /dashboard                                   → {total_invested, total_value, total_pnl, pnl_percent}

GET  /assets                                      → Asset[] with nested holdings
POST /assets                                      → create asset (polymorphic by asset_type)*
DELETE /assets/{asset_id}                         → delete asset + all related data

POST /assets/{asset_id}/sell-crypto               → {quantity} → reduce crypto holding
POST /assets/{asset_id}/redeem-mf                 → {units} → reduce MF holding
POST /assets/{asset_id}/top-up                    → {amount} → add to savings/PPF principal

GET  /valuations/latest                           → latest Valuation per asset
POST /valuations/recalculate                      → refresh all prices, update valuations + snapshot

GET  /snapshots                                   → Snapshot[] ordered by date
GET  /transactions?from={date}&to={date}          → TxRecord[] ordered by date desc (inclusive filters)

GET  /market/crypto/top                           → top 10 CoinGecko coins (INR)
GET  /market/mutual-funds/search?q={query}        → MutualFundScheme[] (min 3 chars, max 20)
GET  /market/mutual-funds/{scheme_code}/nav       → {scheme_code, nav, date}

POST /insights/refresh                            → generate + store AI insights
GET  /insights/latest                             → most recent ai_insights record
```

\* **POST /assets is get-or-create for MF/crypto:** if a holding with the same `scheme_code` (MF) or `coingecko_id` (crypto) already exists, the new buy is **averaged into the existing holding** and that asset is returned — a new asset is NOT created. Fixed-income types always create new. See CLAUDE.md "Critical gotchas".
