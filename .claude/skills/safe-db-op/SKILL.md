---
name: safe-db-op
description: Guardrails to follow before any operation that mutates or deletes data in the Investment Tracker database — deleting assets, bulk edits, testing create/delete flows against the live DB, running destructive SQL, or anything that could lose real portfolio data. Load this whenever a task involves changing or removing existing data.
---

# Safe DB operations

This is a single-user app whose Postgres data lives only in the Docker volume `postgres_data`. **There are no backups** (`backup.sh` has never run), so destructive mistakes are irreversible.

## Before any destructive or mutating op
1. **Capture current state** so you can rebuild by hand if needed:
   ```bash
   mkdir -p /tmp/it-snapshot
   curl -s http://127.0.0.1:8000/assets        > /tmp/it-snapshot/assets.json
   curl -s http://127.0.0.1:8000/transactions  > /tmp/it-snapshot/transactions.json
   curl -s http://127.0.0.1:8000/valuations/latest > /tmp/it-snapshot/valuations.json
   ```
2. **Confirm exactly which rows you'll touch** and that they are not real holdings. List `/assets` and match by id, not by name.

## The merge trap (caused real data loss once)
`POST /assets` is **get-or-create for MF and crypto**: if a holding with the same `scheme_code` (MF) or `coingecko_id` (crypto) exists, the new buy is **averaged into that existing asset** and its id is returned — no new asset is created. So:
- Never create "test" MF/crypto using a `scheme_code`/`coingecko_id` that a real asset already holds — it silently mutates the real asset, and a later `DELETE` of that id cascades the real asset + its transactions + valuation history away.
- For tests, use a unique name **and** an identifier not in the portfolio, or a scratch database. Delete only ids you created. Prefer the `e2e-ui-test` skill, which is self-cleaning.

## Real identifiers currently held (do not reuse for tests)
Check live before assuming — `curl -s http://127.0.0.1:8000/assets | python3 -m json.tool`. As of this writing the portfolio holds MF scheme `118347` (nifty 50). Any held scheme/coin is off-limits for throwaway data.

## After the op
Re-list `/assets` and `/dashboard`; if anything unexpected changed, restore from the `/tmp/it-snapshot` capture immediately and report it.
