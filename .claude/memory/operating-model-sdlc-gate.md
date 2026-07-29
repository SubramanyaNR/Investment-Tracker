---
name: operating-model-sdlc-gate
description: WealthSignal runs a lean AI operating model — 7 review lenses + a CEO approval gate enforced by a hook; use /feature for any non-trivial change
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 16f72de1-a089-43c6-9a6a-9cf5ef75f940
---

This repo operates as a lean AI engineering org. The founder is the **CEO**; gated changes require
explicit "approved" before implementation.

- **Run `/feature <request>`** for any non-trivial change: it produces Product → Architecture →
  Security → Engineering → QA reviews (7 lenses: PM, Investor Advisor, CTO, Architect, Eng Lead, QA,
  Security), then **STOPS at the CEO gate**. Implement only the approved scope, then validate.
- **Gated (needs approval):** architecture, data model/migrations, auth, security, product
  direction, infra, prod deploy. A PreToolUse hook (`.claude/hooks/gate.sh`) blocks Edit/Write/
  `make migrate` on gated code paths (`backend/app/**`, `frontend/{app,components,lib}/**`,
  migrations, Makefile, next.config.ts, config.py) unless `.claude/state/feature-approved` exists
  (<12h) or `.claude/state/OVERRIDE` is touched. `/feature` writes the marker after approval.
- **Free lane (no gate):** docs (`docs/**`, `*.md`, `.claude/**`), tests, copy polish within scope.
- **Docs are keyed, loaded on demand via `docs/INDEX.md`:** `operating-model/` (SDLC, ROLES,
  GOVERNANCE), `architecture/` (+ `decisions/` ADRs, scaffold with `/adr`), `product/`, `features/`,
  `runbooks/`. CLAUDE.md stays lean (~100 lines) and navigational.

**Why:** solo founder wanted a sustainable AI-assisted SDLC that protects architecture/data/auth/
security/product/infra decisions and prevents feature creep, while keeping velocity for docs/tests.

**How to apply:** never edit gated code without an approved `/feature`; keep CLAUDE.md under ~300
lines; put architecture in `docs/architecture/*`, features in `docs/features/*`, ops in
`docs/runbooks/*`; record significant technical decisions as ADRs. Built 2026-06-04 on
`feature/supabase-auth`. Related: [[security-audit-and-hardening-backlog]].
