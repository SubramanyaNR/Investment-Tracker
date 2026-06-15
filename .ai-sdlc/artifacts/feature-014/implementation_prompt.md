# Implementation Prompt

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


## Planning
## Review: FastAPI `on_event` → `lifespan` Migration

### Summary Verdict

**Approve for implementation.** This is a clean, well-scoped deprecation fix with no behavioral change and no governance gate implications.

---

### Product Lens

No user-facing impact. This is internal plumbing. The change eliminates a deprecation warning that would otherwise accumulate as a low-grade noise source in CI output, obscuring real warnings over time. Worth fixing.

---

### Architecture Lens

The `lifespan` pattern is the correct FastAPI idiom as of v0.93+. The `asynccontextmanager` approach is cleaner than `on_event` because it makes teardown logic explicit (code after `yield`) and co-locates startup/shutdown in one place. The proposed migration is architecturally aligned with the stack.

One thing to verify before implementing: check whether `main.py` also has a `@app.on_event("shutdown")` handler. If it does, the lifespan context manager must include shutdown logic after the `yield`. The fix request only shows the startup side — the implementer should audit both.

---

### Engineering Lead Lens

Scope is correctly constrained to `backend/app/main.py`. No new dependencies are introduced (`contextlib.asynccontextmanager` is stdlib). Execution order is preserved. This is the minimum change that solves the problem.

The `app = FastAPI(lifespan=lifespan)` line must come **after** the lifespan function is defined — a subtle ordering constraint if the file currently defines the `app` instance near the top and wires event handlers below it. The implementer should reorder if needed.

---

### QA Lens

Success criteria are sensible:
1. App starts — verifiable by running the server or an existing smoke test.
2. Warning gone — verifiable with `pytest -W error::DeprecationWarning` or inspecting pytest output.
3. Integration tests pass — the existing suite covers this.

No new tests are needed for this change. The existing integration tests are the validation surface.

---

### Security Lens

No auth, no JWT handling, no data access changes. Zero security surface impact.

---

### Governance Gate

This change does **not** touch architecture, data model, auth, security model, or infrastructure strategy. It is a within-scope refactor of the app entrypoint using a stdlib pattern. No CEO approval required.

---

### Implementation Notes for the Implementer

1. Read the full current `main.py` before editing — confirm whether a `shutdown` handler exists alongside `startup`.
2. If there are multiple `on_event("startup")` decorators (sometimes seen when routers register their own), each must be folded into the single lifespan function in call order.
3. After the change, run `pytest -W error::DeprecationWarning` to confirm the warning is eliminated, not just suppressed.
4. The `FastAPI(lifespan=lifespan)` constructor argument supersedes any `on_event` registrations — do not leave both in the file.
