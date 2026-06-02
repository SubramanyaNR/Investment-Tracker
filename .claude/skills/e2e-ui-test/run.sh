#!/usr/bin/env bash
# Runs the E2E UI harness against the production frontend. Idempotent setup:
# makes Playwright resolvable from frontend/, ensures chromium, runs from the
# frontend dir (ESM resolves node_modules there), cleans up the temp copy.
set -uo pipefail
FRONTEND=/opt/investment-tracker/frontend
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${1:-http://127.0.0.1:3000}"

# 1. Make `playwright` importable from frontend/node_modules.
if [ ! -e "$FRONTEND/node_modules/playwright" ]; then
  NPX_PW_DIR="$(ls -d /root/.npm/_npx/*/node_modules 2>/dev/null | head -1)"
  if [ -n "${NPX_PW_DIR:-}" ] && [ -e "$NPX_PW_DIR/playwright" ]; then
    ln -sf "$NPX_PW_DIR/playwright" "$FRONTEND/node_modules/playwright"
    ln -sf "$NPX_PW_DIR/playwright-core" "$FRONTEND/node_modules/playwright-core"
  else
    (cd "$FRONTEND" && npm i -D --no-save playwright >/dev/null 2>&1) || { echo "could not install playwright"; exit 2; }
  fi
fi

# 2. Ensure a browser is installed (no-op if already cached).
if ! ls /root/.cache/ms-playwright/chromium* >/dev/null 2>&1; then
  (cd "$FRONTEND" && npx --yes playwright install chromium) || { echo "could not install chromium"; exit 2; }
fi

# 3. Run the harness from the frontend dir, then clean up.
cp "$SKILL_DIR/e2e.mjs" "$FRONTEND/.e2e-skill.mjs"
trap 'rm -f "$FRONTEND/.e2e-skill.mjs"' EXIT
( cd "$FRONTEND" && BASE_URL="$BASE_URL" node .e2e-skill.mjs )
