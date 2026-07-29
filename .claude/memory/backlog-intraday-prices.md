---
name: backlog-intraday-prices
description: Feature backlog — intraday price tracking to enable 1D chart range on Net Worth chart
metadata: 
  node_type: memory
  type: project
  originSessionId: ec6b2875-068b-4043-aca1-ceae6fb02876
---

1D range on the Net Worth chart is not currently meaningful because snapshots are user-triggered daily, not intraday. To support a real 1D chart:

- Crypto: CoinGecko `/coins/{id}/market_chart?vs_currency=inr&days=1` returns hourly prices — viable
- Mutual Funds: AMFI publishes NAV once per day — true intraday is impossible for MFs
- FI (FD/RD/PPF): fixed income, no intraday movement by definition

**Why:** User noted the 1D button on the chart has no real meaning with current daily snapshot model. Should not be shown until intraday data exists.

**How to apply:** When scoping this, note that intraday is crypto-only. Would require a new intraday price store (separate from `portfolio_snapshots`), a scheduler to fetch hourly CoinGecko prices, and a dedicated intraday chart view. Non-trivial schema + infra work. Deferred post-VPS.
