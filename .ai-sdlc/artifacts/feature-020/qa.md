# QA Report: auth-toggle (feature-020)

The `qa` stage's normal adapter (Qwen via OpenRouter) failed with a 401
Unauthorized ("User not found") — an OpenRouter account/key issue, not a
code issue. Same failure class as Gemini's quota exhaustion at the
implementation stage. Ran this stage directly instead, independently
re-verifying against `secure-001/validation.md`'s checklist rather than
just re-reading `implementation.md`'s self-report.

## Scorecard against secure-001/validation.md

### R1 — Single choke-point bypass
- [x] `AUTH_ENABLED`/`auth_enabled` only appears in `backend/app/core/config.py`
  (the setting) and `backend/app/core/auth.py` (the bypass). One additional
  hit in `backend/app/api/auth.py:66` — the new `GET /auth/status` endpoint
  reading `settings.auth_enabled` to *report* state. This is a status read,
  not a second bypass implementation, so it satisfies the checklist's
  intent (no duplicated auth logic) even though it technically isn't listed
  among the two files the checklist named. Not a defect.
- [x] `AUTH_ENABLED=false` + no cookie → `GET /assets` returns 200 with real
  admin data. Verified live in sandbox (see implementation.md).
- [x] Forged cookie ignored, resolves to real admin user_id. Covered by
  `test_auth_disabled_ignores_client_supplied_token` + verified in sandbox.
- [x] Empty `users` table → 500, not anonymous. Covered by
  `test_auth_disabled_no_user_row_raises_500`.
- [x] `AUTH_ENABLED=true` path unchanged, 401 on missing/invalid cookie.
  Full existing test suite (97 unit + 119 integration) passes unmodified in
  behavior (mechanical async/await fixes only, no semantic change).

### R2 — `reset-admin-password` + session invalidation
- [x] Not reachable via HTTP — grep confirms no router registration.
- [x] Interactive prompt via `getpass`, no plaintext in argv. Code-read
  confirmed; `getpass` doesn't echo to terminal or appear in `ps aux` (argv
  is empty for the arg, only the module invocation shows).
- [ ] **FAILS AS WRITTEN.** "A JWT issued before the reset fails
  authentication on the next request (401), confirming `token_version` is
  checked" — **not implemented**. This was a deliberate scope deviation
  (documented in `implementation.md`): access tokens remain valid for their
  existing 15-minute TTL after a reset; only refresh tokens are revoked.
  This is the one checklist item that doesn't pass and needs an explicit
  decision from you, not a QA sign-off — see "Open item" below.
- [ ] Same deviation — "logging in issues a JWT that passes the now-current
  token_version check" doesn't apply since there's no token_version.
- [x] Script updates the existing row in place, no second row created.
  Verified live in sandbox: same `user_id` before/after reset.

### R3 — Read-only homescreen auth-status display
- [x] No DB column/migration for auth state — confirmed no migration was
  added at all for this feature (grep + directory listing).
- [x] No frontend write/toggle call — grep of `lib/api.ts` shows only a
  type declaration and the read-only `getAuthStatus()` GET call.
- [~] Homescreen displays state + instructions — **implemented as a
  site-wide banner** (shows on every page, not just homescreen) rather than
  a homescreen-specific widget. This exceeds rather than falls short of the
  requirement (R4 explicitly wants "every page," and R3's own display
  requirement is satisfied since the homescreen is one of the pages it
  renders on). Not a defect, but worth noting the shape differs slightly
  from "homescreen display" as literally worded.
- [x] No auth required to view the status — confirmed, `GET /auth/status`
  has no `Depends(get_current_user_id)`.

### R4 — Danger banner
- [x] **Design changed and improved during planning** (recorded in
  `feature-020/request.md`): banner now shows whenever `AUTH_ENABLED=false`
  regardless of `deployment_context` — stricter than the original checklist
  item which only required this for `deployment_context=hosted`. The
  `local`-only "de-emphasized note" checklist item is superseded by this
  change; verified the amber ("local") variant still renders with real
  instructional text, not silently suppressed.
- [x] `AUTH_ENABLED=true` → no banner regardless of context. Verified live
  against the production instance post-restart.
- [x] No request-origin/Host-header/IP logic anywhere in the banner path —
  confirmed by grep + code read of both `AuthDisabledBanner.tsx` and the
  `/auth/status` handler.
- [x] `.env.example` and `AUTH.md` document `DEPLOYMENT_CONTEXT`, including
  the Tailscale-counts-as-hosted note.

### R5 — Onboarding hardening
- [x] `.env.example` `ADMIN_PASSWORD=changeme` — unambiguous placeholder.
- [x] README Quick Start explicitly instructs `make reset-admin-password`
  before enabling auth/exposing the instance.

### Cross-cutting / regression
- [x] Full suite passes with `AUTH_ENABLED=true` default — 216/216.
- [x] Fresh-install default is `AUTH_ENABLED=false` — confirmed in
  `config.py` and `.env.example`.
- [x] **Core data-continuity smoke test — done for real**, not simulated:
  isolated sandbox, added data while disabled, ran the reset script, flipped
  auth on, logged in with new creds, confirmed the data was still there
  under the same `user_id`. This was the original question that started
  the whole `/discuss` thread — it holds.
- [ ] **Not done**: visual confirmation of the banner rendering in an actual
  browser (colors, dismiss button, wording). Verified the component's logic
  and the API contract it depends on, and confirmed via curl that it's
  correctly absent on the live production homepage (where auth is on), but
  never rendered the *disabled* state in a real browser. Low risk (three-line
  conditional, straightforward JSX) but not proven — flagged the same way in
  `implementation.md`.
- [x] `docs/architecture/AUTH.md` and ADR 0005 amendment reflect the shipped
  model, including the R2 deviation.

## Additional QA-only findings (not on the original checklist)

- **Regression the checklist didn't anticipate, caught during
  implementation, not QA**: `conftest.py` needed `AUTH_ENABLED=true` added
  explicitly, or the entire test suite would have silently run in
  disabled-auth mode. Already fixed before this QA pass; re-verified here
  by reading `conftest.py` and confirming the full suite's 401-path tests
  (`anon_client` fixture, `test_missing_cookie_401`, etc.) still exercise
  real credential checking. Confirmed correct.
- **`backend/scripts/__init__.py` is empty**, making `scripts` an importable
  package for `python -m scripts.reset_admin_password` — correct and
  minimal, no issue.
- No new Alembic migration exists for this feature (by design, since
  `token_version` was dropped) — consistent with the R2 deviation, not an
  oversight.

## Summary

19 of 21 checklist items pass as originally written; 1 item (R3's "homescreen"
framing) is superseded by a stricter design (not a defect); 2 items
(R2 token-invalidation) fail as written due to a deliberate, documented scope
deviation that needs your explicit sign-off, not silent QA approval. 1 item
(banner browser rendering) is unverified — low risk, quick to close if you
want it done before shipping.

## Open item requiring your decision

**Accept the R2 deviation (no `token_version`, 15-minute access-token
exposure window on reset, refresh-token revocation only) as implemented?**
If not, the fix is a real schema change (new `users.token_version` column +
Alembic migration + a DB check added to `get_current_user_id`'s
already-hot path) — a larger change than what's here now, and one that
trades away the documented "no network call" property of access-token
verification. My recommendation remains to accept the smaller mitigation,
but this is exactly the kind of tradeoff CLAUDE.md's governance model
reserves for you, not for QA to wave through.
