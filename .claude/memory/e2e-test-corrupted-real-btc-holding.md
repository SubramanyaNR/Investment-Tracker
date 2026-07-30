---
name: e2e-test-corrupted-real-btc-holding
description: "e2e-ui-test harness merged test buys into the real BTC holding on 2026-07-30 because it assumed \"bitcoin\" was an unheld, safe test identifier — it wasn't. Fixed data + hardened harness with a live check."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4ad21862-5ab8-4926-88c0-88f8decd0117
  modified: 2026-07-30T10:20:53.220Z
---

On 2026-07-30 (post-VM-migration), running the `e2e-ui-test` skill corrupted the real BTC holding.
The harness's crypto step hardcoded `bitcoin` as "not held; safe" — a comment written once and never
re-verified. This account actually holds BTC (`0.011 @ avg ₹76,67,829.64`, from two real buys:
2022-01-15 and 2026-06-03). Running the harness twice merged two extra `0.01 BTC @ ₹50,00,000` test
buys into it via `POST /assets`' get-or-create-by-`coingecko_id` behavior (see
[[post-assets-merges-by-scheme-or-coin]]), corrupting it to `0.031 @ ₹59,46,649.23`.

**Root cause:** the harness (and the `safe-db-op` skill's "known held identifiers" list) recorded a
point-in-time safety assumption as a permanent fact in a comment/doc, instead of checking live every
run. The `safe-db-op` doc's held-scheme list was *also* stale/wrong (listed `118347`, actual held
schemes are `153531` and `120503`) — nobody had corrected it either.

**Fix applied:** Diagnosed via the two 2026-07-30-dated transactions (identical units/price/amount,
today's date — real transactions were dated 2022 and 2026-06-03). Deleted the 2 bad transaction rows
and reset `crypto_holdings.quantity`/`avg_buy_price` to the correct weighted average of the real buys,
via a direct `asyncpg` transaction against `ADMIN_DATABASE_URL` (no delete-transaction API endpoint
and no recompute-from-history service function exist — see [[ai-sdlc-model-adapters-verified]]-style
note: checked via an Explore agent first, confirmed no safer existing path). Verified the fix through
the real `/assets` and `/transactions` API responses, not just the DB.

**Hardening applied:** `e2e.mjs` now fetches `/api/assets` live at the start of every run and:
- picks the first `parag`-search MF result whose `scheme_code` isn't already held
- picks the first top-10 coin whose `coingecko_id` isn't already held
- aborts loudly if no safe option exists, instead of silently merging

**Why this matters:** this is the second time the exact same merge trap has caused real data
mutation on this single-user, no-backups production DB (see [[post-assets-merges-by-scheme-or-coin]]
for the first incident, an MF scheme). Any hardcoded "X is safe/unheld" claim in code, comments, or
skill docs for this app is a time bomb — the portfolio changes over time and the claim doesn't.

**How to apply:** Never trust a "safe identifier" claim in this codebase (code comments, skill docs,
or memory) without re-verifying live against `/assets` first. When writing test/automation tooling
against this app, prefer computing safety dynamically (as `e2e.mjs` now does) over hardcoding an
identifier and a comment asserting it's fine. Related: [[post-assets-merges-by-scheme-or-coin]],
[[no-db-backups-exist]].
