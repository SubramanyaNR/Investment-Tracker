# QA Prompt

## Product Context
# Product Context - WealthSignal

WealthSignal is a personal multi-asset portfolio tracker for Indian retail investors. It provides unified portfolio observability (net worth, P&L, allocation) across crypto, mutual funds, and fixed income (FD/RD/PPF).

Key Principles:
- Portfolio observability is the primary goal.
- Not a trading or brokerage app.
- Focus on clarity and trust for the retail investor.


## Architecture Context
# Architecture Context

Stack:
- Backend: FastAPI (Python 3.11), SQLAlchemy 2.0 (async), Pydantic.
- Frontend: Next.js 16 (App Router), React 19, Tailwind 4.
- Database: Postgres 16 (UUID PKs, Numeric for money).
- Auth: Supabase Auth (PKCE flow).

Key Patterns:
- Same-origin /api proxy for backend access.
- All DB operations must be async.
- Identity derived only from verified JWT 'sub' claim.
- RLS enforced as a backstop; app-layer filtering is mandatory.


## Investor Experience Context
# Investor Experience Context

Investor Trust & Clarity:
- Metric comprehension: Are units and calculations clear?
- Dashboard clarity: Mobile-first status at a glance.
- Investor trust: Presentation must build confidence; limitations must be clear.
- Presentation of insights: Language must be investor-friendly, not overly technical.


## Planning
# Feature Planning: Onboarding Flow (First-Run Modal)

**Workflow ID:** feature-005  
**Request:** Onboarding Flow — First-Run Experience for New Users  
**Estimate:** 5–7 days (backend flag + frontend modal + integration test)  
**Priority:** HIGH (conversion killer fix, pre-VPS)

---

## 1. Product Review

**Problem Statement:**  
Current flow: User signs up → blank dashboard → no context → abandons.  
New flow: User signs up → dashboard shows onboarding prompt → guides first asset entry → dashboard populates → user sees value.

**User Value:**  
- ✅ Reduces signup-to-first-action friction
- ✅ Demonstrates app value immediately (populated dashboard)
- ✅ Increases conversion rate (first asset is a strong engagement signal)
- ✅ No cognitive load (one button: "Add First Asset")

**Acceptance:**  
- Does it improve portfolio observability? **YES** — empty dashboards undermine observability until user has data. This converts signups into actual portfolios.
- Does it fit product principles? **YES** — pure UX improvement; no scope creep. Single-step onboarding, not multi-step wizard.

**Verdict:** ✅ **APPROVED BY PM**  
Clear user value, minimal scope, high conversion impact. Proceed.

---

## 2. Architecture Review

**Changes:**
- Backend: Add `onboarding_completed` boolean to `users` table
- Backend: Dashboard `/dashboard` endpoint returns `is_onboarding_eligible` flag
- Frontend: New `OnboardingOverlay` component (modal wrapper)
- Database: One-time migration (Alembic)

**API Impact:**  
GET `/dashboard` response gains one boolean field:
```json
{
  "is_onboarding_eligible": false,
  "total_invested": 50000,
  ...
}
```

**Service Impact:**  
- Dashboard service unchanged (new field is computed at response time)
- No new endpoints
- No new external APIs

**Overengineering Check:**  
- ✅ Not overengineered (single boolean flag, computed from existing data)
- ✅ Reuses existing add-asset modal (no new UI components required beyond overlay wrapper)
- ✅ Monolith-first (no new services)

**Verdict:** ✅ **APPROVED BY CTO/ARCHITECT**  
Minimal, cleanly scoped. Schema addition is justified (persistent flag across sessions). Proceed.

---

## 3. Security Review

**Auth/Identity:**
- Overlay trigger: `is_onboarding_eligible` computed from `users.id` (JWT `sub`) ✅
- No client-supplied data in eligibility check ✅
- User can only see their own onboarding status ✅

**Multi-Tenancy:**
- Each user sees their own flag; no cross-user leakage ✅
- RLS backstop: `users` table has implicit user_id scoping ✅

**Data Exposure:**
- `onboarding_completed` flag: no sensitive data ✅
- Dashboard response includes no new user PII ✅

**API Abuse Surface:**
- No new endpoints introduced ✅
- Existing rate limiting on `/dashboard` applies ✅
- Boolean flag has no side effects (read-only from client perspective) ✅

**Verdict:** ✅ **APPROVED BY SECURITY REVIEWER**  
No new attack surface. Clean identity handling. Proceed.

---

## 4. Engineering Plan

### Files Affected

**Backend:**
- `backend/app/db/models.py` — Add column to User model
- `backend/app/db/migrations/` — Create migration (Alembic)
- `backend/app/api/dashboard.py` (or similar) — Add `is_onboarding_eligible` to response schema
- `backend/app/services/dashboard.py` — Compute flag (count assets, check column)

**Frontend:**
- `frontend/components/OnboardingOverlay.tsx` — NEW (modal wrapper, ~80 lines)
- `frontend/app/page.tsx` (dashboard) — Import and conditionally render overlay
- `frontend/lib/api.ts` — Add `is_onboarding_eligible` to DashboardResponse type

**Tests:**
- `backend/tests/integration/test_onboarding.py` — NEW (test overlay trigger + persistence)
- Manual test plan (golden path + edge cases)

### Sequence

1. **Migration** (1 hour)
   - Add `onboarding_completed` boolean column to users
   - Backfill all existing users to TRUE (not first-run)
   - `make migrate m="Add onboarding_completed flag to users"`

2. **Backend Response** (30 min)
   - Update Dashboard pydantic schema: add `is_onboarding_eligible: bool`
   - Compute: `COUNT(assets) == 0 AND onboarding_completed == false`
   - Return flag to frontend

3. **Frontend Component** (2 hours)
   - OnboardingOverlay component: modal + heading + CTA + close button
   - Import AddAssetModal
   - Wire "Add First Asset" button to trigger modal

4. **Dashboard Integration** (1 hour)
   - Dashboard component: conditionally render overlay if eligible
   - After first asset persists, backend auto-sets flag; overlay disappears

5. **Testing** (2–3 hours)
   - Integration test: new user → overlay → add asset → flag set ✅
   - Regression test: existing user → no overlay ✅
   - Manual: full flow in browser

### Migration Requirements

**Must use Alembic:**
```bash
make migrate m="Add onboarding_completed flag to users"
```
Creates reversible migration. Backfill existing users immediately.

**Verdict:** ✅ **APPROVED BY ENGINEERING LEAD**  
Clear sequence, minimal surface. Estimate 5–7 days is realistic (largest chunk is testing). Proceed.

---

## 5. QA Plan

### Test Scenarios

**Scenario 1: New User Onboarding (Golden Path)**
1. Create new user account (signup)
2. Land on dashboard → overlay appears (modal visible, non-blocking)
3. Click "Add First Asset" → existing add-asset modal launches
4. Enter crypto (e.g., BTC, $1000) → submit
5. Overlay disappears; dashboard shows asset in holdings
6. Refresh page → overlay does NOT reappear (flag persisted)
7. **Verdict:** ✅ Overlay gate working, persistence working

**Scenario 2: Existing User (No Overlay)**
1. Create user account
2. Add asset immediately (before dashboard load)
3. Land on dashboard → overlay does NOT appear
4. Dashboard shows holdings normally
5. **Verdict:** ✅ No false positives

**Scenario 3: Overlay Dismiss Behavior**
1. New user (no assets) → dashboard loads
2. Overlay appears; click close button
3. Overlay disappears (session state)
4. Refresh page → overlay reappears (flag not set yet)
5. Add asset; overlay gone permanently
6. **Verdict:** ✅ Session-only dismiss, persistence on first asset

**Scenario 4: Deleted Assets Edge Case**
1. New user → add asset → set flag to TRUE
2. Delete asset (user changes mind)
3. Overlay should NOT reappear (flag is TRUE, not dependent on asset count)
4. **Verdict:** ✅ Flag prevents re-showing

**Edge Cases:**
- [ ] Rapid ADD asset + refresh (race condition) — overlay should not flicker
- [ ] Mobile responsiveness (390px) — modal is usable on small screens
- [ ] Accessibility (overlay is keyboard-navigable, screen-reader friendly)
- [ ] No console errors in browser DevTools

### Auth & Multi-Tenancy Re-Validation

Per SECURITY-AUDIT.md §7:
- [ ] User A sees overlay, adds asset → User A's assets shown (not B's)
- [ ] User B logs in → overlay for User B (separate flag)
- [ ] Cross-user asset fetch → 404 (existing RLS, no regression)

### Regression Risks

- Dashboard load time — fetching asset count shouldn't add latency (negligible)
- Add-asset modal — reused without changes; no regression expected
- Existing user experience — flag backfill ensures zero impact

**Verdict:** ✅ **APPROVED BY QA LEAD**  
Clear test plan covers golden path, edge cases, and regression. Auth/multi-tenancy validated. Proceed.

---

## 6. Investor Experience Review

**Activation Rule Check:**  
Feature matches: "New user onboarding, UI change affecting first impression"  
→ Investor Experience Review **required** ✅

### Comprehension & Trust

**Metric Clarity:**  
- Overlay is not a metric; it's a UX prompt. No confusion. ✅

**Dashboard Clarity:**  
- Empty dashboard (before first asset) was confusing.
- Prompt "Add your first investment to get started" is action-oriented and clear. ✅

**Investor Trust:**  
- Does overlay build or erode confidence?
  - Builds: Shows the app is interactive, guiding the investor through first steps.
  - No red flags: Simple, non-aggressive, dismissible. ✅

**Information Hierarchy:**  
- Overlay is modal (prominent) but doesn't obscure dashboard.
- Single CTA prevents decision paralysis. ✅

**Mobile Usability:**  
- Modal must be 390px-friendly (full width, touch-friendly button).
- Criteria: button ≥48px, readable text, no horizontal scroll.  
→ Must verify in testing

**Presentation of Insights:**  
- Copy: "Welcome to WealthSignal" + "Add your first investment to get started"
- Tone: Friendly, not corporate. ✅
- Language: Plain English, no jargon. ✅

**Verdict:** ✅ **APPROVED BY INVESTOR EXPERIENCE REVIEWER**  
Overlay builds confidence and engagement. Clear, investor-friendly prompt. Mobile-friendly requirement flagged for testing. Proceed.

---

## 7. ⛔ CEO APPROVAL GATE

**All 7 lenses: APPROVED**

| Lens | Verdict | Notes |
|---|---|---|
| Product Manager | ✅ APPROVED | High-value, low-scope, conversion killer fix |
| Investor Advisor | ✅ APPROVED | Retail investor perspective: guides new users intuitively |
| CTO | ✅ APPROVED | Monolith-first, no overengineering, schema addition justified |
| Architect | ✅ APPROVED | Clean API, minimal surface, reuses existing components |
| Engineering Lead | ✅ APPROVED | 5–7 day estimate realistic; clear sequence |
| QA Lead | ✅ APPROVED | Test plan complete; regression risks low |
| Security Reviewer | ✅ APPROVED | No new attack surface; identity/tenancy clean |
| Investor Experience | ✅ APPROVED | Builds confidence; mobile-friendly requirement noted |

### CEO Sign-Off Required Before:
- [ ] Creating Alembic migration
- [ ] Writing backend/frontend code
- [ ] Touching `users` table schema

**Status:** 🛑 **AWAITING CEO APPROVAL**

---

## Implementation Readiness

**Approved Scope:**
- Add `onboarding_completed` boolean to users table (Alembic migration)
- Dashboard endpoint returns `is_onboarding_eligible` flag
- OnboardingOverlay component (modal, reuses AddAssetModal)
- Integration test covering new-user flow + persistence
- Mobile responsiveness check (390px+)

**Out of Scope (deferred):**
- Multi-step onboarding wizard (single step only)
- Tips/help text on next actions (defer to post-MVP)
- Email reminders (out of scope)

**Known Assumptions:**
- Existing add-asset modal is complete and working ✅
- Dashboard component can conditionally render overlays ✅
- Alembic migration process is understood (runbooks/LOCAL-DEV.md) ✅

**Next Step:**  
CEO approval → `/approve feature-005` → Gemini implements → Qwen tests → Claude audits → ship

---

## AUDIT ROUND 1 — FIXES REQUIRED (CEO Approved)

The first audit pass identified three issues. The two medium-severity items must be fixed before release. Implementation is by Gemini (file edits only — no shell commands). Do not re-implement anything already working.

---

### Fix 1 — RLS on `users` table (Medium — Security)

**Context:** Every user-owned table in this project has a `tenant_isolation` RLS policy (see migration `6a8bdc1bb742`). The `users` table introduced in `8dcb4a0b4e27` was omitted. The existing pattern uses `user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid` but the `users` table is keyed by `id` (UUID primary key = Supabase `sub`), so the policy condition must use `id` instead.

**Task:** Create a new Alembic migration file at `backend/alembic/versions/<new_revision_id>_add_rls_to_users_table.py` with:

```python
"""add RLS to users table

Revision ID: <generate a short unique hex string, e.g. a1b2c3d4e5f6>
Revises: 8dcb4a0b4e27
Create Date: <today>
"""
from alembic import op

revision = '<new_revision_id>'
down_revision = '8dcb4a0b4e27'
branch_labels = None
depends_on = None

_USING = "id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"

def upgrade() -> None:
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON users FOR ALL "
        f"USING ({_USING}) WITH CHECK ({_USING})"
    )

def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
```

Replace `<new_revision_id>` with a unique 12-character hex string. Do NOT run `alembic upgrade head` — migrations are applied by the human operator.

---

### Fix 2 — Close/dismiss button on OnboardingOverlay (Medium — Functional)

The approved plan required a close (X) button for session-only dismissal: overlay disappears until refresh; adding an asset makes it permanent. The current implementation has no close button.

**Task A — Update `frontend/components/OnboardingOverlay.tsx`:**

Add `onDismiss: () => void` to the `Props` interface. Add an X close button in the top-right corner of the modal card (absolute position, top-3 right-3). The button must:
- Use `onClick={onDismiss}`
- Be keyboard accessible (type="button")
- Match the existing theme tokens (`var(--text-secondary)` for the icon, `var(--bg-elevated)` for the card background already in place)
- Use a simple SVG X icon (same strokeWidth/strokeLinecap style as the existing + icon in the component)

**Task B — Update `frontend/app/page.tsx`:**

1. Add `const [isDismissed, setIsDismissed] = useState(false)` near the other state declarations (the file already imports `useState` from React).
2. Change the `OnboardingOverlay` render at line ~382 from:
   ```tsx
   <OnboardingOverlay 
     isVisible={dashboard.is_onboarding_eligible} 
     onAddFirstAsset={() => setTab("holdings")} 
   />
   ```
   To:
   ```tsx
   <OnboardingOverlay 
     isVisible={dashboard.is_onboarding_eligible && !isDismissed} 
     onAddFirstAsset={() => setTab("holdings")}
     onDismiss={() => setIsDismissed(true)}
   />
   ```

---

### Fix 3 — ORM column definition (Low — Cosmetic, fix while touching models.py)

In `backend/app/db/models.py`, the `onboarding_completed` column uses only a Python-side default. Update it to also declare `nullable=False` and `server_default` so the ORM definition matches the DB schema:

```python
# before
onboarding_completed: Mapped[bool] = mapped_column(default=False)

# after
onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
```

Ensure `Boolean` is imported from `sqlalchemy` (it is already used elsewhere in models.py or can be added to the existing sqlalchemy import).

---

### Summary of files to edit

| File | Change |
|---|---|
| `backend/alembic/versions/<new_id>_add_rls_to_users_table.py` | NEW — RLS migration |
| `backend/app/db/models.py` | Update `onboarding_completed` column definition |
| `frontend/components/OnboardingOverlay.tsx` | Add `onDismiss` prop + X button |
| `frontend/app/page.tsx` | Add `isDismissed` state + pass `onDismiss` prop |

No other files should be modified. Do not run any shell commands.

---

## AUDIT ROUND 2 — FIX REQUIRED (CEO Approved)

One functional bug was found in the Audit Round 2 review. All other fixes passed. Only the item below needs to change — do not touch any other file.

### Fix — CTA button must dismiss the overlay

**File:** `frontend/app/page.tsx`  
**Line:** ~385 (the `onAddFirstAsset` prop on the `OnboardingOverlay` component)

**Problem:** Clicking "Add First Asset" calls `setTab("holdings")` but leaves `isDismissed` as `false`. The overlay has `fixed inset-0 z-[100] bg-black/70 backdrop-blur-md` — it remains covering the entire screen. The user cannot see or reach the holdings tab underneath and is stuck until they separately click the X button.

**Exact change required:**

```tsx
// BEFORE (current code)
onAddFirstAsset={() => setTab("holdings")}

// AFTER
onAddFirstAsset={() => { setTab("holdings"); setIsDismissed(true); }}
```

That is the only change. Do not modify any other file. Do not run any shell commands.


## Implementation
I have completed the implementation of all fixes required from Audit Rounds 1 and 2 for the Onboarding Flow (feature-005).

### Summary of Changes

#### Security & Backend
- **RLS on `users` table:** Verified the existence and content of the Alembic migration `backend/alembic/versions/a1b2c3d4e5f6_add_rls_to_users_table.py`, which correctly enables Row Level Security and enforces tenant isolation using the verified JWT 'sub' claim (`id`).
- **ORM Model Refinement:** Updated `backend/app/db/models.py` to ensure the `onboarding_completed` column in the `User` model is strictly defined with `Boolean`, `nullable=False`, and a `server_default="false"`.

#### Frontend & UX
- **Dismissible Onboarding Overlay:** Enhanced `frontend/components/OnboardingOverlay.tsx` with an `onDismiss` prop and a styled 'X' close button (keyboard accessible, theme-compliant) for session-only dismissal.
- **Improved Interaction Flow:** Updated `frontend/app/page.tsx` to:
    - Manage the `isDismissed` state.
    - Pass the `onDismiss` handler to the overlay.
    - **(Audit Round 2 Fix)**: Ensure that clicking the "Add Your First Investment" CTA button also dismisses the overlay, preventing it from blocking the UI once the user transitions to the holdings tab.

These changes ensure the onboarding experience is secure, user-friendly, and functions correctly across all intended interactions.

```tsx
// frontend/app/page.tsx - Audit Round 2 Fix Applied
<OnboardingOverlay 
  isVisible={dashboard.is_onboarding_eligible && !isDismissed} 
  onAddFirstAsset={() => { setTab("holdings"); setIsDismissed(true); }}
  onDismiss={() => setIsDismissed(true)}
/>
```
