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
# Fix Request: FastAPI on_event Deprecation

## Summary

`backend/app/main.py` uses `@app.on_event("startup")` to run startup logic (scheduler init, DB warmup). This API is deprecated in FastAPI and produces a `DeprecationWarning` in every test run:

```
DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.
```

## Required Change

Replace `@app.on_event("startup")` with the modern `lifespan` pattern using `@asynccontextmanager`.

### Before
```python
@app.on_event("startup")
async def startup():
    await do_something()
```

### After
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await do_something()
    yield

app = FastAPI(lifespan=lifespan)
```

## Scope

- **File:** `backend/app/main.py` only
- **No behavior change** — same startup logic, same execution order
- **No schema, auth, or infrastructure changes**
- **No new dependencies**

## Success Criteria

1. App starts correctly with lifespan handler
2. Deprecation warning no longer appears in pytest output
3. All existing integration tests pass

