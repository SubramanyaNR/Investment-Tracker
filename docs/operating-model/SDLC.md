# SDLC — how WealthSignal ships

> This is the operating contract for every non-trivial change. Run it via `/feature`.
> It encodes one system reasoning through **seven lenses** and stopping at **one approval gate**.
> The founder (CEO) approves; nothing in the gated set is executed without an explicit "approved".

## The model: seven lenses + multi-agent specialization + one approval gate

The SDLC runs through **seven review lenses** (one system reasoning, not seven agents), then **delegates implementation and QA to specialist models** via the AI-SDLC framework. Claude orchestrates; Gemini implements; Qwen tests; Claude audits. Every stage requires explicit CEO approval before proceeding. Full mandates: `ROLES.md` and `INVESTOR-EXPERIENCE-REVIEW.md`.

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

**Browser Behavior Compatibility (required for any frontend change):**
For every frontend element that uses browser-native behavior — `<a href>`, `<form action>`,
`window.location`, file download, redirect — explicitly answer:
> *"Does this mechanism send the `Authorization` header? Is the target endpoint compatible with
> the authentication state the user is in when they trigger this action?"*

Browser navigation cannot send custom headers. An authenticated `fetch()` can. Mismatch = silent
auth failure from the user's perspective. Flag and resolve before implementation, not after.

### Step 5 — QA Plan
Test scenarios · edge cases · regression risks · **auth + multi-tenancy re-validation**
(re-run `runbooks/SECURITY-AUDIT.md` §7 matrices).

**QA scenarios must include at least one user-journey test per user-facing action.**
For every interactive element (button, link, download, form, upload) write at least one scenario
as a user outcome, not an API contract:

> ✅ "User clicks 'Download template' → file downloads in browser" (user outcome)
> ❌ "GET /template returns 200 with text/csv" (API contract — necessary but not sufficient)

Also check the correct **client type** for each test: authenticated user via API ≠ browser
navigation. Anonymous access, browser-native downloads, and unauthenticated paths each require
their own test scenario — not a variant of the authenticated API test.

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
After CEO approval, the implementation intent is handed off to **Gemini** (implementation specialist).
Gemini implements **only** the approved scope — no unrelated improvements, no "while I'm here" refactors,
no redesign unless requested. Claude monitors handoff and surfaces any implementation blockers to the CEO.

### Step 8 — QA
Gemini's implementation is handed off to **Qwen** (QA specialist) for test execution and validation.
Qwen runs test scenarios, edge cases, regression checks, and re-validates auth + multi-tenancy (SECURITY-AUDIT §7 matrices).
QA artifacts are stored and surface any failures to Claude for triage.

### Step 9 — Audit & Final Approval
Claude audits the implementation + QA results against the original approval scope. If all validation passes:
- Implementation is complete; surfaces it back to CEO
- If failures exist, Claude reports them to CEO with recommended actions (rework, waive, or abandon)

## Post-implementation validation (non-negotiable)

Encoded in `runbooks/LOCAL-DEV.md`. Qwen executes these as part of Step 8 QA; Claude verifies completion:

1. `make build` — frontend **production** build succeeds (`npm run build` + `npm run start`, not dev-only).
2. Run test suite (unit + integration; SECURITY-AUDIT §7 matrices for auth/tenancy validation).
3. `make validate` — backend health + `/api` proxy.
4. **Auth still works** + **multi-tenancy still works** (two-user isolation, 401-without-token, cross-user IDOR → 404).
5. `e2e-ui-test` skill for affected + adjacent UI. **Mandatory when any user-facing UI was added or changed — not optional.**
6. **User Journey Walkthrough** — for every interactive element added or changed, trace the full user action from click/tap through to outcome. Ask: *"Can the user actually do what this feature promises?"* This is not test execution; it is deliberate outcome verification. A feature is not complete if a user cannot complete its primary workflow.
7. Fix → repeat until clean.

## AI-SDLC Multi-Agent Workflow Execution

The AI-SDLC framework automates Steps 1–6 (review), hands off Steps 7–8 (implementation + QA) to specialist models, then Claude returns for Step 9 (audit).

### Workflow Types

- `feature` — new functionality or changes to existing features
- `architecture` — data model, API, or service boundary changes
- `security` — auth, isolation, or threat-model changes
- `release` — production deployment or major version work
- `incident` — urgent fixes requiring expedited review
- `discuss` — discussion/exploration (not gated)

### Workflow Lifecycle

Every feature/architecture/security/release/incident workflow follows this sequence:

1. **Planning** — Claude reasons through the 7 lenses, produces review artifacts
2. **CEO Approval Gate** — STOP. Wait for explicit "approved"
3. **Implementation** — Gemini takes the approved scope and implements it
4. **QA** — Qwen validates the implementation (tests, edge cases, regression, auth/tenancy matrices)
5. **Audit** — Claude audits implementation + QA results against approval scope
6. **CEO Approval Gate** — STOP. Wait for explicit "approved" to ship
7. **Complete** — Feature lands; artifacts archived

No automatic advancement between stages. Every gate is explicit.

### Workflow State & Artifacts

Workflow state is stored in:
```
.ai-sdlc/artifacts/<feature-name>/status.yaml
```

Artifacts include:
- `request.md` — original user request (preserved in full)
- `planning.md` — the 7-lens review + verdicts
- `planning_prompt.md` — the exact prompt used for planning
- `implementation.md` — what Gemini produced
- `implementation_prompt.md` — the implementation brief
- `qa.md` — Qwen's test results + validation matrix
- `qa_prompt.md` — the QA brief
- `audit.md` — Claude's final audit + recommendations
- `status.yaml` — workflow metadata (stage, models, timestamps)

### Model Routing

Model assignments are defined in `.ai-sdlc/models.yaml`:

| Stage | Model | Role |
|---|---|---|
| Planning + Audit | Claude | Orchestrator; reasons through all 7 lenses |
| Implementation | Gemini (default) | Implements the approved scope |
| QA | Qwen (Alibaba Qwen 3.2B via OpenRouter) | Tests, validates, re-runs SECURITY-AUDIT §7 |

**Model ownership is mandatory.** If an assigned model is unavailable, misconfigured, returns only placeholder output, or errors out:
- The workflow stops at that stage
- Claude reports the failure to the CEO
- The CEO chooses: fix the model, remap the stage, perform manual validation, or waive the stage
- Claude may recommend options but does not choose autonomously

### Using the Workflow

Run the `/feature` command (or `/architecture`, `/security`, etc.) with your request:
```
/feature Add real-time price updates to dashboard
```

Claude automatically:
1. Detects the workflow type
2. Reads the request in full
3. Produces the 7-lens review
4. Stops at the CEO gate
5. On approval, hands off to the assigned specialist models via status.yaml
6. Monitors execution and surfaces results

No manual invocation of individual models needed — Claude orchestrates the handoff.

## Defaults this SDLC enforces
- Monolith-first. No microservices / K8s / CQRS / event-sourcing / event-driven without an
  extraordinary, written justification (CTO + Architect must both sign off).
- Simplicity, maintainability, developer velocity over cleverness.
- Strict multi-tenancy; JWT-derived identity; ownership checks that don't leak existence.
- Build for 0–100 users now, able to reach 500 without re-architecture.

## AI-SDLC Workflow Execution

Claude Code is the primary interface for AI-SDLC.

Users interact with Claude rather than directly invoking workflow scripts.

### Workflow Types

* feature
* discuss
* architecture
* security
* release
* incident

### Workflow Request Handling

When a workflow command is used, all content following the command is treated as the workflow request.

The request may contain:

* Context
* Goals
* Constraints
* Requirements
* Acceptance Criteria
* Questions
* Links
* Screenshots
* Notes

The request should be preserved in full and stored as the workflow request artifact.

### Workflow Lifecycle

1. Workflow Created
2. Planning
3. Approval
4. Implementation
5. Approval
6. QA
7. Approval
8. Audit
9. Approval
10. Complete

Every stage requires explicit approval.

No automatic advancement is permitted.

### Workflow Discovery

Claude should determine the active workflow automatically whenever possible.

Workflow state is stored in:

.ai-sdlc/artifacts/<workflow>/status.yaml

Only request a workflow identifier when multiple active workflows create ambiguity.

### Model Routing

Model ownership is defined by:

.ai-sdlc/models.yaml

Current routing:

* Planning → Claude
* Implementation → Gemini
* QA → Qwen
* Audit → Claude

Claude acts as the orchestrator.

Gemini acts as the implementation specialist.

Qwen acts as the QA specialist.

Model ownership is mandatory.

If a model assigned to a workflow stage is unavailable, misconfigured, returns an execution error, or produces only placeholder output, the workflow must stop.

Claude must not substitute itself for the assigned model.

Claude must report the failure and wait for CEO direction.

Possible CEO actions include:
- Fix the model integration
- Remap the stage to another model
- Perform manual validation
- Explicitly waive the stage

Claude may recommend options but may not choose one autonomously.

### Artifacts

Workflow artifacts may include:

* request.md
* planning.md
* implementation.md
* qa.md
* audit.md
* status.yaml

Artifacts are the source of truth for workflow state and workflow outputs.
