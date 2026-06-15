# Release: feature-013 — Pagination on GET /assets

**Released:** 2026-06-15  
**Released by:** CEO (approved)

---

## What Shipped

`GET /assets` is now paginated, matching the existing transactions endpoint pattern.

### Changes

| File | Change |
|---|---|
| `backend/app/api/assets.py` | Added `limit`/`offset` params, envelope response, COUNT(*) query, stable sort |
| `frontend/lib/api.ts` | Added `AssetPage` type; `getAssets()` fetches all pages transparently |
| `backend/tests/integration/test_assets_pagination.py` | New — 6 tests covering pagination, edge cases, sort |
| `backend/tests/integration/test_tenant_isolation.py` | Updated for envelope shape |
| `backend/tests/integration/test_csv_import.py` | Updated for envelope shape |
| `backend/tests/integration/test_onboarding.py` | Updated for envelope shape |
| `backend/tests/integration/test_manual_assets.py` | Updated for envelope shape (Gemini) |
| `backend/tests/integration/test_auth_isolation.py` | Updated for envelope shape (Gemini) |

### API Change

**Before:** `GET /assets` → `[...assets]`  
**After:** `GET /assets?limit=N&offset=N` → `{"items": [...], "total": N, "limit": N, "offset": N}`

Default: first 50 assets, sorted `asset_type ASC, name ASC`.

Frontend consumers are unaffected — `getAssets()` returns a flat array as before.

---

## Validation

- 210 integration tests passing
- Manual validation approved by CEO
- No schema changes, no migrations, no auth changes

---

## Lessons Learned

1. **Gemini missed imports** — `Query` and `func` were used but not imported in `assets.py`. The app would have failed to start. Pre-QA smoke test (can the app even import?) would catch this class of error cheaply.
2. **Gemini missed 3 test files** — response shape changes need a project-wide grep for all callers. Gemini updated 2 files but missed 3 others. The QA pre-hook (pytest) surfaced the failures.
3. **Test fixture had invalid UUID** — `pppppppp-pppp-pppp-pppp-pppppppppppp` is not valid hex. Qwen caught this from the pytest collection output. Good signal that the pytest pre-hook is earning its keep.
4. **No cleanup in seed fixture** — fixed-income assets have no unique constraint, so each test run accumulated new rows. Pattern: any fixture that POSTs assets must DELETE them first (or use the `admin_engine` truncate approach).
