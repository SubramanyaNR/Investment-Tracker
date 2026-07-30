---
name: e2e-ui-test
description: Run end-to-end UI tests against the production frontend in a real headless browser (Playwright). Use when asked to verify or validate the frontend, test the UI, confirm a change works in the real app, or run a production-build smoke test of the Investment Tracker.
---

# E2E UI test (production build, real browser)

Drives the live frontend with headless Chromium and checks every core flow: dashboard load, theme toggle, asset-type switching, MF/crypto search, add Mutual Fund / Crypto / FD / RD / PPF, list update, valuation refresh, sell crypto, transactions — then **deletes everything it created** and asserts a clean DB.

## How to run
The app must already be running in production mode (`make dev` or `make restart`). The app is
auth-gated, so a real login is required — pass credentials as env vars, never hardcode them in the
script or commit them anywhere:

```bash
E2E_EMAIL=... E2E_PASSWORD=... bash .claude/skills/e2e-ui-test/run.sh                       # tests http://127.0.0.1:3000
E2E_EMAIL=... E2E_PASSWORD=... bash .claude/skills/e2e-ui-test/run.sh http://172.23.80.6:3000   # tests via the VM IP (the real browser path — verify it's actually reachable first, e.g. curl; it may not be from inside the VM depending on network setup)
```

If the login screen isn't shown (already-authenticated session), the credentials are simply unused.
`run.sh` is idempotent: it makes Playwright importable from `frontend/`, ensures a chromium browser
is installed, runs the harness, and cleans up. Exit code is non-zero if any check fails. Read the
`PASS/FAIL` lines plus the `console errors` / `api failures` summary.

## Safety (important)
The harness is self-cleaning and only ever touches assets named `SKILLTEST *`. **Never assume any
specific scheme/coin is "safe" or unheld** — this account's real holdings change over time, and this
harness has previously corrupted a real BTC holding by assuming `bitcoin` wasn't held when it was.
`POST /assets` merges by `scheme_code`/`coingecko_id`: a buy against an already-held identifier
averages into that real holding instead of creating a new one, silently, with no created-row to
delete during cleanup.

The harness now fetches `/api/assets` live at the start of every run and picks the MF (from the
`parag` search) and crypto (from the top-10 list) to test with dynamically, skipping any identifier
that's already held, and aborts loudly if no safe option exists. Do not revert this to a hardcoded
identifier. There are no DB backups — if you ever do suspect a merge into a real holding, stop
immediately and use the `safe-db-op` skill before touching anything else.

## If a check fails
1. Reproduce, then read `/tmp/it-backend.log` and `/tmp/it-frontend.log`.
2. Fix the root cause, `make build` / `make restart`, re-run this skill.
3. The harness selectors track `frontend/app/page.tsx` and the selector components — if the UI markup changes, update `e2e.mjs` selectors to match.
