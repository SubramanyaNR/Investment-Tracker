# Planning Prompt

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


## Governance Context
# Governance Context

Operating Model:
- One system, seven lenses (PM, Investor Advisor, CTO, Architect, Eng Lead, QA, Security).
- Hard CEO approval gate at Step 6 of SDLC.
- Gated decisions: Architecture, Data Model, Auth, Security, Product Direction.
- Free lane: Docs, tests, copy polish within approved scope.


## Investor Experience Context
# Investor Experience Context

Investor Trust & Clarity:
- Metric comprehension: Are units and calculations clear?
- Dashboard clarity: Mobile-first status at a glance.
- Investor trust: Presentation must build confidence; limitations must be clear.
- Presentation of insights: Language must be investor-friendly, not overly technical.


## Request
# Onboarding Flow — First-Run Experience for New Users

## Problem

Current state: User signs up → blank dashboard → confused → abandons app

This is a **conversion killer**. New users have no holdings yet, so the dashboard is empty and uninviting. They don't know what to do next.

## Goal

Guide new users through their first investment entry immediately after signup, so they see a populated dashboard and understand the app's value.

## Requirements

### 1. Detect First-Time User
- User has no assets in portfolio (query `assets` table, user_id = jwt.sub)
- First-run flag is NOT set in database (add column if needed)

### 2. Show One-Time Onboarding Overlay
When first-time user lands on dashboard:
- Modal/overlay appears with:
  - Heading: "Welcome to WealthSignal"
  - Subheading: "Add your first investment to get started"
  - CTA button: "Add First Asset" (launches add-asset modal)
  - Optional close button (dismiss, but show once more on refresh until first asset added)
  
### 3. Trigger Add-Asset Modal
- Clicking "Add First Asset" button launches the existing add-asset modal
- No new UI needed — reuse existing flow

### 4. Mark First-Run Complete
- After first asset is successfully added:
  - Set first-run flag in database (e.g., `onboarding_complete = true`)
  - Overlay never appears again for that user

### 5. No Regression
- Existing users (already have assets) see no overlay
- Dashboard behavior unchanged for returning users

## Acceptance Criteria

### Functional
- [ ] First-time user (0 assets) sees onboarding overlay on dashboard load
- [ ] Overlay disappears when first asset is added
- [ ] Existing users (with assets) see no overlay
- [ ] Re-login by same user shows no overlay (flag persisted)
- [ ] Overlay close button works (optional dismiss)

### User Experience
- [ ] Overlay is non-intrusive but prominent (modal, not toast)
- [ ] Copy is clear and action-oriented
- [ ] Modal triggers add-asset flow without friction
- [ ] First asset appears on dashboard after submission

### Testing
- [ ] Manual test: new user signup → dashboard → overlay → add first crypto → dashboard populated
- [ ] Manual test: existing user with assets → no overlay
- [ ] Manual test: overlay persists on refresh until first asset added
- [ ] No console errors or accessibility issues

## Out of Scope

- Email reminders ("complete your profile")
- Multi-step onboarding tour (just one prompt)
- Guided tour of other features (that's post-launch)
- Risk questionnaire or KYC (deferred)

## Priority

**HIGH** — High conversion impact. Do before VPS launch.

## Estimate

5–7 days (backend flag + frontend modal + integration test)

## Design Decisions

### First-Run Flag Storage
- **Decision:** Add `onboarding_completed` boolean column to `users` table
- **Why:** Persists across sessions; doesn't break if user deletes their first asset later
- **Migration required:** Yes — add column with default FALSE, backfill existing users to TRUE (they're not first-run)

### First-Time User Detection
- **Logic:** `onboarding_completed = false AND COUNT(user_assets) = 0`
- **Reason:** Prevents accidental re-showing if user deletes all assets (unlikely but possible)
- **Fallback:** If table query fails, hide overlay (no show-stopping errors)

### Overlay Behavior (Option A - Chosen)
- **Close button:** Hides overlay for current session ONLY (frontend state, not persisted)
- **Reappear:** Overlay reappears on next login/refresh until first asset is added
- **Why:** Gentle nudge; doesn't feel pushy; user can dismiss and come back later without friction
- **After first asset:** Set `onboarding_completed = true` in database; overlay never shows again
- **No temporary flags or expiry:** Keep it simple — either completed (first asset added) or not (show on refresh)

### Backend
- New migration: Add `onboarding_completed` column to users
- Existing `/assets` POST endpoint already handles asset creation; no new endpoint needed
- Add backend check on dashboard data fetch: return `"is_onboarding_eligible": onboarding_completed == false AND COUNT(assets) == 0`

### Frontend
- New component: `OnboardingOverlay` (modal wrapper)
- Show overlay in Dashboard component if `is_onboarding_eligible == true`
- "Add First Asset" button launches existing `AddAssetModal`
- After asset creation, overlay auto-hides (asset appears on dashboard)

## Notes

- TASKS-BEFORE-VPS.md lists this as P2 (can start pre-VPS)
- Consider: should overlay show tips for next steps? (CSV import, XIRR, etc.) — defer to post-MVP if time allows
- This is NOT a multi-step wizard; it's a single prompt that launches existing flow
- Zero risk to existing users: `onboarding_completed` defaults to TRUE on backfill

