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
<!-- Artifact template: feature request -->

# Feature Request: Transaction Date Filter

## User Request
Add optional `from` and `to` query parameters to `GET /transactions` so users can filter their transaction history by date range.

## Endpoint Change
**Existing:** `GET /transactions?limit=N&offset=N`
**Updated:** `GET /transactions?limit=N&offset=N&from=YYYY-MM-DD&to=YYYY-MM-DD`

Both `from` and `to` are optional. If omitted, existing behaviour is unchanged (return all transactions paginated).

## Requirements
- `from` — inclusive start date (ISO 8601: YYYY-MM-DD)
- `to` — inclusive end date (ISO 8601: YYYY-MM-DD)
- Both optional; either can be supplied independently
- Invalid date format → 422 Unprocessable Entity
- `from` > `to` → 422 with clear error message
- Filtered results still respect `limit`/`offset` pagination
- Auth unchanged: only the requesting user's transactions returned
- No schema changes required

## Frontend
No frontend changes in this scope — the filter params are for API consumers. Backend only.

## Acceptance Criteria
1. `GET /transactions?from=2026-01-01&to=2026-06-01` returns only transactions in that range
2. `GET /transactions` (no filter) unchanged — all transactions paginated as before
3. `from` only or `to` only work independently
4. Invalid date → 422
5. `from` > `to` → 422
6. Cross-user isolation unchanged — filter never leaks another user's transactions
7. Integration tests cover all above cases

## Estimated Effort
0.5–1 day (backend only, small change to existing query)

