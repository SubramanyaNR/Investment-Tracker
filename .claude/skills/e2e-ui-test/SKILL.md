---
name: e2e-ui-test
description: Run end-to-end UI tests against the production frontend in a real headless browser (Playwright). Use when asked to verify or validate the frontend, test the UI, confirm a change works in the real app, or run a production-build smoke test of the Investment Tracker.
---

# E2E UI test (production build, real browser)

Drives the live frontend with headless Chromium and checks every core flow: dashboard load, theme toggle, asset-type switching, MF/crypto search, add Mutual Fund / Crypto / FD / RD / PPF, list update, valuation refresh, sell crypto, transactions — then **deletes everything it created** and asserts a clean DB.

## How to run
The app must already be running in production mode (`make dev` or `make restart`). Then:

```bash
bash .claude/skills/e2e-ui-test/run.sh                       # tests http://127.0.0.1:3000
bash .claude/skills/e2e-ui-test/run.sh http://172.23.80.6:3000   # tests via the VM IP (the real browser path)
```

`run.sh` is idempotent: it makes Playwright importable from `frontend/`, ensures a chromium browser is installed, runs the harness, and cleans up. Exit code is non-zero if any check fails. Read the `PASS/FAIL` lines plus the `console errors` / `api failures` summary.

## Safety (important)
The harness is self-cleaning and only ever touches assets named `SKILLTEST *`. It deliberately uses a Mutual Fund (`parag` search) and coin (`bitcoin`) **not held** in the real portfolio, because `POST /assets` merges by `scheme_code`/`coingecko_id` — reusing a real identifier would mutate real data. Never edit the harness to use a held scheme/coin. There are no DB backups.

## If a check fails
1. Reproduce, then read `/tmp/it-backend.log` and `/tmp/it-frontend.log`.
2. Fix the root cause, `make build` / `make restart`, re-run this skill.
3. The harness selectors track `frontend/app/page.tsx` and the selector components — if the UI markup changes, update `e2e.mjs` selectors to match.
