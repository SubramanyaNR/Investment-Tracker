## Manual validation — performed by Claude (2026-08-10)

Consolidates everything already validated across `qa.md` and the audit follow-ups — no new work in
this stage, just the closing checklist per SDLC.md's lifecycle.

- [x] 211 automated tests (92 unit, 119 integration against a real, freshly-migrated Postgres)
- [x] 15 live adversarial `curl` checks against the actual cut-over instance (not mocks)
- [x] Real-browser e2e (`e2e-ui-test` skill, headless Chromium, production build): sign-in,
      dashboard load, theme toggle, asset-type switching all pass
- [x] Login/session verified against both real access paths: `http://167.233.141.50:3000`
      (plaintext public IP) and `https://madhyastha-lab-server.tail40a80c.ts.net` (Tailscale HTTPS)
- [x] Schema verified directly via `psql`: 12 tables, RLS off on all of them, `app_user` role present
- [x] Two real bugs caught and fixed before this point: `manual_holdings` RLS omission,
      `_complete_onboarding`'s NOT-NULL violation on upsert-insert
- [x] Admin recovery runbook written (`docs/runbooks/ADMIN-ACCOUNT-RECOVERY.md`)
- [x] Tech debt logged (`ROADMAP.md`): RLS regression-coverage loss, refresh-token family-revocation
      gap, stale Supabase/RLS doc references, `COOKIE_SECURE=false` on a public IP
- [x] Founder account left in its genuine real state post-testing: 0 assets, onboarding not
      completed, no stray active refresh tokens

## Known, explicitly accepted, not blocking
- `COOKIE_SECURE=false` transports the session in plaintext over the public-IP path — a conscious
  consequence of the O5 decision (`FEATURE-BACKLOG.md`), not an oversight; flagged for the founder
  to weigh explicitly, not silently fixed or silently ignored.
- Refresh-token rotation revokes only the reused token, not its whole lineage — acceptable for a
  single-user threat model, logged as tech debt for if that ever changes.
- Both QA and this implementation were performed by Claude rather than the assigned Gemini/Qwen
  models, due to two independent tooling failures (Gemini daily quota, invalid OpenRouter API key)
  — founder-directed in both cases, documented in `implementation.md`/`qa.md`. No independent model
  verified this code; flagged explicitly, not left implicit.
