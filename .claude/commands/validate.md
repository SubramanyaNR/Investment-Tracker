---
description: Validate the app against a production build
---

Validate the app the production way (never dev-mode):

1. `make build` — confirm it compiles with no errors.
2. `make restart` — postgres + backend (127.0.0.1:8000) + frontend prod (:3000).
3. `make validate`, then `curl -s http://127.0.0.1:3000/api/dashboard` — confirm the same-origin /api proxy returns data.
4. If anything fails: read `/tmp/it-backend.log` and `/tmp/it-frontend.log`, find root cause, fix, rebuild, recheck. Loop until green.

Rules:
- Do NOT test against the live DB using real `scheme_code`/`coingecko_id` — POST /assets merges by those (see CLAUDE.md). Use unique names + unheld identifiers, and delete anything you create.
- Report: build result, health, any errors found/fixed.
