---
name: post-assets-merges-by-scheme-or-coin
description: POST /assets for MF/crypto MERGES into an existing holding with the same scheme_code/coingecko_id (average-in) instead of creating a separate asset
metadata: 
  node_type: memory
  type: project
  originSessionId: dbda2e20-cd6a-4ff9-91bb-5abf9f86e313
---

`create_asset` in `backend/app/api/assets.py` does get-or-create: for MUTUAL_FUND it looks up an existing `MutualFundHolding` by `scheme_code`, and for CRYPTO by `coingecko_id`. If found, it **averages the new buy into the existing holding** (weighted units/NAV or qty/price) and returns the EXISTING asset's id — it does NOT create a new asset. Fixed-income types always create new.

**Why it matters:** During testing on the live single-user DB this is dangerous. Creating a "temp" MF with a `scheme_code` that an existing real asset already uses will silently mutate that real asset (and a later DELETE of the "temp" id cascade-wipes the real asset + its transactions + valuation_history). This happened once: the real "nifty 50" (scheme 118347) was clobbered and had to be rebuilt from values captured at session start. Its prior transaction history and original created_at were unrecoverable.

**How to apply:** Never reuse a real asset's scheme_code/coingecko_id for throwaway test data on the production DB. Use a clearly unique name AND a scheme/coin not already held, or test against a scratch database. There are NO db backups — see [[no-db-backups-exist]].
