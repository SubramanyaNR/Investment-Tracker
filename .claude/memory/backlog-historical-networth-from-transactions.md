---
name: backlog-historical-networth-from-transactions
description: "Feature backlog — reconstruct historical net worth from transaction history to show full investment journey, not just from WealthSignal signup"
metadata: 
  node_type: memory
  type: project
  originSessionId: ec6b2875-068b-4043-aca1-ceae6fb02876
---

The Net Worth chart currently starts from when WealthSignal first recorded a snapshot. Transaction history can extend years before that (imported via CSV). User wants the full investment journey reflected in the chart.

**Approach:** Reconstruct point-in-time portfolio value by replaying transactions + fetching historical market prices:
- Crypto: CoinGecko `/coins/{id}/market_chart?vs_currency=inr&days=max` — daily historical prices available
- MF: MFAPI has full historical NAV per scheme_code
- FI: Analytical — compound interest formula gives value at any past date, no external API needed

**Output:** Backfill `portfolio_snapshots` with reconstructed daily rows from first transaction date to first real snapshot. One-time async job, triggered on user request or at migration time.

**Why:** Only historical reconstruction gives the user a complete view of their investment journey — the core observability promise of WealthSignal. Without it, a user who has invested for 5 years but joined WealthSignal 3 months ago sees 3 months of data.

**How to apply:** Significant work. Requires async job architecture (APScheduler or background task), rate-limit awareness (CoinGecko 30 req/min free tier), and schema consideration (distinguish `source='reconstructed'` from `source='live'` in `portfolio_snapshots`). Flag as medium-complexity, high-value roadmap item.
