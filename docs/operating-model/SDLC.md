# SDLC — how WealthSignal ships

> This is the operating contract for every non-trivial change. Run it via `/feature`.
> It encodes one system reasoning through **seven lenses** and stopping at **one approval gate**.
> The founder (CEO) approves; nothing in the gated set is executed without an explicit "approved".

## The model: one system, seven lenses + conditional specialist, one gate

There are **no separate agents**. For any change I reason through the seven review perspectives
below in a single pass, plus a conditional eighth lens (Investor Experience Reviewer) if the feature
is investor-facing. Surface each verdict, then halt at the CEO gate. Full mandates: `ROLES.md`
and `INVESTOR-EXPERIENCE-REVIEW.md`.

| Lens | One-line mandate |
|---|---|
| Product Manager | "Why before how." User value + acceptance criteria. Reject feature creep. |
| Investor Advisor | The persona (₹50k–₹5L/mo, Kuvera/Zerodha/MProfit/Excel) — would they use & understand it? |
| CTO | Long-term architecture, cost, tech-debt, build-vs-buy. Block premature complexity. |
| Architect | Data model, API, service boundaries, domain modelling. Prevent overengineering. |
| Engineering Lead | File-level plan, sequence, migration strategy. Keep scope minimal. |
| QA Lead | "Assume it breaks." Edge cases, regression, test plan. |
| Security Reviewer | Pessimist. AuthN/Z, multi-tenancy, IDOR, secrets, API abuse. Attackers > developers. |
| **Investor Experience Reviewer** | **[Conditional]** "Can the investor understand and trust this metric/dashboard/insight?" Comprehension + trust review. |

## The 6 steps + gate

For every feature request, produce in order:

### Step 1 — Product Review
Problem being solved · user value · alternatives considered · **does it improve portfolio
observability?** (If not, stop here — see `product/PRINCIPLES.md`.)

### Step 2 — Architecture Review
Database impact · API impact · service impact · overengineering check (monolith-first default).

### Step 3 — Security Review
Risks · isolation concerns · authentication/authorization concerns · API-abuse surface.
Identity is **always** derived from the verified JWT `sub`, never from client input.

### Step 4 — Engineering Plan
Files affected · migration requirements (`make migrate`) · implementation sequence.

### Step 5 — QA Plan
Test scenarios · edge cases · regression risks · **auth + multi-tenancy re-validation**
(re-run `runbooks/SECURITY-AUDIT.md` §7 matrices).

### Step 5.5 — Investor Experience Review (Conditional)

**Only if:** Feature matches activation rules in `docs/operating-model/INVESTOR-EXPERIENCE-REVIEW.md`.

Produce **Investor Experience Review** report covering:
- **Metric comprehension:** Is the metric self-explanatory? Are units and calculations clear?
- **Dashboard clarity:** Information hierarchy correct? Can investor understand status at a glance (on mobile)?
- **Investor trust:** Does presentation build or erode confidence? Are limitations clear?
- **Presentation of insights:** Is language investor-friendly? Are caveats and confidence levels clear?
- **Information hierarchy:** Is the most critical data prominent? Does new element fit the existing dashboard?
- **Mobile usability:** Does this work on 390px? Are interactive elements usable on touch?

Report to CEO as input for approval decision. **Advisory only.** Does not block approval.

See example output in `ROLES.md` under "Investor Experience Reviewer."

### Step 6 — ⛔ CEO APPROVAL GATE
**STOP. Wait for explicit approval.** Do not call Edit/Write/`make migrate` on gated scope
(see `GOVERNANCE.md` for what is gated) until the CEO says "approved".

### Step 7 — Implementation
Implement **only** the approved scope. No unrelated improvements, no "while I'm here" refactors,
no redesign unless requested.

## Post-implementation validation (non-negotiable)

Encoded in `runbooks/LOCAL-DEV.md`; never declare success without it:

1. `make build` — frontend **production** build succeeds (`npm run build` + `npm run start`, not dev-only).
2. Run tests (until a suite exists, the SECURITY-AUDIT §7 matrices stand in for auth/tenancy).
3. `make validate` — backend health + `/api` proxy.
4. **Auth still works** + **multi-tenancy still works** (two-user isolation, 401-without-token, cross-user IDOR → 404).
5. `e2e-ui-test` skill for affected + adjacent UI.
6. Fix → repeat until clean.

## Defaults this SDLC enforces
- Monolith-first. No microservices / K8s / CQRS / event-sourcing / event-driven without an
  extraordinary, written justification (CTO + Architect must both sign off).
- Simplicity, maintainability, developer velocity over cleverness.
- Strict multi-tenancy; JWT-derived identity; ownership checks that don't leak existence.
- Build for 0–100 users now, able to reach 500 without re-architecture.
