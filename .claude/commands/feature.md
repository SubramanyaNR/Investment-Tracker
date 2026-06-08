---
description: Run the WealthSignal SDLC review for a change and stop at the CEO approval gate. Usage: /feature <request>
---

You are running the WealthSignal operating model for this request: **$ARGUMENTS**

First read `docs/operating-model/SDLC.md`, `docs/operating-model/ROLES.md`, `docs/operating-model/GOVERNANCE.md`,
and `docs/operating-model/INVESTOR-EXPERIENCE-REVIEW.md`. Load only the additional docs the request
touches, using `docs/INDEX.md` routing (e.g. `architecture/DATA-MODEL.md` for schema, `architecture/AUTH.md`
for auth, `product/PRINCIPLES.md` for scope).

Reason through the seven lenses and produce, in order, with each lens's verdict made explicit:

### 1. Product Review
Problem · user value · alternatives · **does it improve portfolio observability?** (PM + Investor
Advisor). If it fails the PRINCIPLES test, say so and stop.

### 2. Architecture Review
Database · API · service impact · overengineering check (CTO + Architect). Default monolith-first.

### 3. Security Review
Risks · isolation · authN/Z · API-abuse surface (Security Reviewer, pessimistic). Identity from JWT
`sub` only; ownership checks don't leak existence.

### 4. Engineering Plan
Files affected · migration requirements · implementation sequence (Engineering Lead). Minimum surface.

For any frontend element using browser-native behavior (`<a href>`, form action, file download,
redirect): explicitly state whether the target endpoint allows unauthenticated access and whether
the mechanism is compatible with the endpoint's auth requirements.

### 5. QA Plan
Test scenarios · edge cases · regression risks · auth + multi-tenancy re-validation (QA Lead).

For each user-facing interactive element, include at least one scenario as a **user outcome**
(*"User clicks X → Y happens"*) tested with the correct client type (browser-navigation ≠
authenticated fetch). Do not rely solely on authenticated API tests to validate browser-native
interactions.

### 5.5 Investor Experience Review (if applicable)
Check `docs/operating-model/INVESTOR-EXPERIENCE-REVIEW.md`. If the feature matches an activation
rule, produce Investor Experience Review report. Otherwise, skip.

### 6. ⛔ CEO APPROVAL GATE
**STOP here.** Present the above and ask the CEO to approve, revise, or reject. Do **not** call
Edit/Write/`make migrate` on any gated path (see GOVERNANCE "Gated code paths") yet.

Only after the CEO explicitly approves:
- Write the approval marker so the gate hook unblocks implementation:
  `mkdir -p .claude/state && printf 'scope: %s\napproved_at: %s\n' "$ARGUMENTS" "$(date -Iseconds)" > .claude/state/feature-approved`
- Then implement **only** the approved scope (Step 7) — no unrelated changes.
- Run the post-implementation validation from SDLC.md (`make build`, `make validate`, auth +
  tenancy matrices, `e2e-ui-test` [mandatory for any UI change], User Journey Walkthrough). Fix →
  repeat until clean.
- When the feature lands, remove the marker (`rm -f .claude/state/feature-approved`) and, if it
  shipped, add `docs/features/<feature>.md`.
