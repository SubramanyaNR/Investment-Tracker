# Onboarding Flow (First-Run Modal)

**Feature ID:** feature-005  
**Status:** Shipped  
**Priority:** HIGH  

## What It Does

New users who land on an empty dashboard see a full-screen onboarding overlay prompting them to add their first investment. Once an asset is added the overlay is permanently dismissed (backend flag). The overlay can also be temporarily dismissed per session via a close (X) button — it reappears on refresh until the first asset is added.

## Behaviour

| User State | Overlay Shown |
|---|---|
| New user, zero assets, flag = false | ✅ Yes |
| Existing user with assets | ❌ No |
| New user: clicked X (session dismiss) | ❌ Hidden until refresh |
| New user: added first asset | ❌ Never again (flag = true) |
| New user: deleted all assets after first add | ❌ Never (flag persists) |

## Implementation

### Backend

- **Migration `8dcb4a0b4e27`** — creates `public.users(id UUID PK, onboarding_completed BOOLEAN NOT NULL DEFAULT false)`; backfills existing users with assets to `true`
- **Migration `a1b2c3d4e5f6`** — enables RLS on `users` table with `tenant_isolation` policy keyed on `id` (matches `app.current_user_id` GUC)
- **`backend/app/db/models.py`** — `User` model with `onboarding_completed: Mapped[bool]` (`nullable=False`, `server_default="false"`)
- **`backend/app/services/portfolio.py`** — `get_dashboard` returns `is_onboarding_eligible: bool` (`asset_count == 0 AND NOT onboarding_completed`)
- **`backend/app/api/assets.py`** — `_complete_onboarding` idempotent upsert called after every successful asset creation (all 7 asset type endpoints)

### Frontend

- **`frontend/components/OnboardingOverlay.tsx`** — modal with welcome copy, "Add Your First Investment" CTA, and X dismiss button (session-only)
- **`frontend/app/page.tsx`** — `isDismissed` local state; `isVisible={dashboard.is_onboarding_eligible && !isDismissed}`; CTA calls `setTab("holdings")` + `setIsDismissed(true)`

### Tests

- **`backend/tests/integration/test_onboarding.py`** — new user eligible → add asset → not eligible → delete asset → still not eligible (persistence)

## Operator Checklist (on deploy)

```bash
alembic upgrade head   # applies both migrations: users table + RLS policy
```

## Audit Trail

Three audit rounds were required:
1. Round 1 caught: missing RLS, missing close button, ORM definition gap, fabricated QA report
2. Round 2 caught: CTA button left overlay blocking the viewport after tab switch
3. Round 3: clean pass — all fixes verified

## Known Limitations

- CTA navigates to the holdings tab (not directly to the add-asset modal) — acceptable simplification, one extra click
- `onboarding_completed` flag cannot be reset via UI — intentional; use DB if needed for testing
