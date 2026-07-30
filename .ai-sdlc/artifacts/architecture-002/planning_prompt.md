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
# Architecture Request: Pivot to Open-Source Self-Hosted Single-User Project

## Change requested

The founder has decided (2026-07-30) to pivot WealthSignal's direction and architecture:

- **Product direction:** no longer a hosted SaaS aimed at "the masses" (₹99/mo, 8-crore-investor
  TAM per `docs/product/VISION.md`). Instead, an **open-source project published on GitHub**, run
  by individuals on their own servers/machines. Pricing, trial, Razorpay, and hosted-multi-tenant
  SaaS concerns are out of scope going forward.
- **Deployment model:** **single-user per deployment.** No signup/multi-tenant flow. Simplest
  possible auth — effectively one admin identity per install, not a general-purpose user system.
- **Database:** drop Supabase (managed Postgres) entirely. Self-hosted **Postgres in Docker**,
  packaged so a self-hoster can `docker-compose up` and go.
- **Auth:** drop Supabase Auth (GoTrue) entirely. Replace with **custom auth against vanilla
  Postgres** (e.g. bcrypt password hash + self-issued JWT), implemented directly in the FastAPI
  backend — no external auth service dependency.

This explicitly supersedes and cancels `architecture-001` (VPS cutover for a hosted,
Supabase-backed production instance), which assumed the opposite direction (staying on Supabase,
cutting it over to a real domain for a hosted SaaS). See `architecture-001/status.yaml` for the
cancellation note.

## What this touches (all CEO-gated categories, per `docs/CLAUDE.md`)

- **Architecture** — service boundaries change: no more Supabase as an external identity/DB
  provider; the backend now owns both.
- **Database schema / migrations** — every table currently has RLS `tenant_isolation` policies
  keyed on `app.current_user_id` (see `docs/architecture/AUTH.md`, migrations
  `6a8bdc1bb742_enable_rls_tenant_isolation_policies.py`,
  `a1b2c3d4e5f6_add_rls_to_users_table.py`). Single-user-per-deployment likely means RLS becomes
  unnecessary complexity — needs an explicit decision: rip out RLS, or keep it dormant (single
  fixed user_id) for cheap multi-user optionality later.
- **Authentication model** — full replacement: Supabase JWT verification (JWKS-based, ES256, PKCE
  flow) → self-issued/verified JWT or session auth. This is the single biggest, riskiest piece of
  this change.
- **Security model** — self-hosted Postgres in Docker means there's no managed provider handling
  encryption-at-rest, network isolation, patching, etc. — the self-hoster now owns that surface.
  Docs/defaults need to guide them toward not exposing Postgres publicly, etc.
- **Product direction** — confirmed pivot away from paid SaaS.
- **Infrastructure** — this VM's role changes too: no longer "the" production SaaS server:
  likely becomes the founder's own personal instance / the reference deployment used to build and
  validate the OSS release, and possibly a demo. Roadmap items V1–V8 (Hetzner SaaS provisioning,
  Razorpay, etc.) are largely moot now.

## What does NOT change (confirm to keep review scope honest)

- Core product features (asset tracking, XIRR, CSV import/export, performance movers, onboarding)
  are asset-tracking logic, independent of auth/DB-hosting — should port over mostly unchanged.
- Money-as-Numeric, Alembic-only migrations, async SQLAlchemy — these engineering rules remain.
- CoinGecko/MFAPI integrations are unaffected by this pivot (though the separate `api.mfapi.in`
  network-egress issue on this VM is still open — unrelated to this decision).

## Constraints

- No existing automated test suite gates this; validation will be manual + whatever the
  `e2e-ui-test` skill can cover, updated for the new auth flow.
- This VM currently holds real portfolio data (the founder's own), migrated in from Supabase
  historically. A migration/export path from the current Supabase-backed schema to the new
  self-hosted schema needs to preserve that data — this is a real production data migration, not a
  green-field build.
- Target audience is now "someone technical enough to clone a repo and run docker-compose" —
  informs how much auth hardening / UX polish is warranted (less than a public SaaS, more than a
  pure hobby script, since it still handles real financial data for whoever runs it).

## Governance concerns

This is the largest single change requested in this project's history — it simultaneously touches
every category `docs/CLAUDE.md` lists as requiring CEO approval. Recommend the planning stage
produce a **phased plan** (schema/RLS decision → auth replacement → Docker Postgres packaging →
data migration path → docs/README for self-hosters) rather than a single big-bang implementation,
consistent with how `architecture-001`'s planning review reasoned about phasing. Explicit sign-off
should be sought per phase, not just once for the whole pivot.

