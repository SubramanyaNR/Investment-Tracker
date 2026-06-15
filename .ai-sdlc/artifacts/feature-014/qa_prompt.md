# QA Prompt

You are the QA reviewer for WealthSignal. Your job is to validate implementation quality using real evidence — not implementation notes.

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


## Planning (Approved Spec)
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

## Implementation Notes (What the implementer claims was done)
I have successfully migrated the FastAPI lifecycle events in `backend/app/main.py` from the deprecated `@app.on_event("startup")` pattern to the modern `lifespan` pattern using `asynccontextmanager`.

### Changes performed:
- **`backend/app/main.py`**:
    - Added `from contextlib import asynccontextmanager`.
    - Defined a `lifespan` async context manager that encapsulates the startup logic (starting the scheduler if enabled).
    - Updated the `FastAPI` application instance to use the `lifespan` parameter: `app = FastAPI(..., lifespan=lifespan)`.
    - Removed the deprecated `@app.on_event("startup")` decorator and its associated function.
    - Ensured the `app` instance is created after the `lifespan` function definition to satisfy FastAPI's requirements, while maintaining the correct order for middleware and exception handler registrations.

### Validation:
- **Manual Code Review**: Verified that the logic is identical to the previous implementation (no behavioral change).
- **Architecture Compliance**: The change follows the standard FastAPI 0.93+ idiom as requested.
- **Dependency Check**: Confirmed that `asynccontextmanager` is used correctly from the standard library.
- **Scope Verification**: Searched the entire codebase for other `on_event` handlers and confirmed that `main.py` was the only location requiring migration in the active application logic.

Note: In this specific environment, the `run_shell_command` tool was not available to execute automated tests directly. However, the migration is a straightforward refactor of the application entry point with no complex side effects, and the code has been verified for structural integrity.
Ripgrep is not available. Falling back to GrepTool.
Error executing tool run_shell_command: Tool "run_shell_command" not found. Did you mean one of: "update_topic", "grep_search", "replace"?
[LocalAgentExecutor] Blocked call: Unauthorized tool call: 'run_shell_command' is not available to this agent.
[LocalAgentExecutor] Blocked call: Unauthorized tool call: 'invoke_agent' is not available to this agent.
[LocalAgentExecutor] Blocked call: Unauthorized tool call: 'run_shell_command' is not available to this agent.
[LocalAgentExecutor] Blocked call: Unauthorized tool call: 'invoke_agent' is not available to this agent.
Error executing tool run_shell_command: Tool "run_shell_command" not found. Did you mean one of: "update_topic", "grep_search", "replace"?

## Actual Test Results (Ground truth — pytest output)
## Pytest Results (exit code: 0)

```
........................................................................ [ 34%]
........................................................................ [ 68%]
..................................................................       [100%]
=============================== warnings summary ===============================
app/core/config.py:4
  /opt/investment-tracker/backend/app/core/config.py:4: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class Settings(BaseSettings):

tests/integration/test_auth_jwt.py::test_valid_token_accepted
tests/integration/test_auth_jwt.py::test_expired_token_rejected
tests/integration/test_auth_jwt.py::test_wrong_audience_rejected
tests/integration/test_auth_jwt.py::test_wrong_issuer_rejected
tests/integration/test_auth_jwt.py::test_missing_sub_rejected
tests/integration/test_auth_jwt.py::test_missing_exp_rejected
tests/integration/test_auth_jwt.py::test_non_uuid_sub_rejected
  /opt/investment-tracker/backend/.venv/lib/python3.11/site-packages/jwt/api_jwt.py:147: InsecureKeyLengthWarning: The HMAC key is 11 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
    return self._jws.encode(

tests/integration/test_auth_jwt.py::test_alg_hs256_rejected
  /opt/investment-tracker/backend/.venv/lib/python3.11/site-packages/jwt/api_jwt.py:147: InsecureKeyLengthWarning: The HMAC key is 6 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
    return self._jws.encode(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
210 passed, 9 warnings in 31.58s
```


## Actual Code Changes (Ground truth — real files, not claims)
## Modified Files (git diff HEAD)

```diff
diff --git a/backend/app/main.py b/backend/app/main.py
index fc0ff8d..0b5485a 100644
--- a/backend/app/main.py
+++ b/backend/app/main.py
@@ -1,7 +1,8 @@
 import time
 import uuid
+from contextlib import asynccontextmanager
 
 from fastapi import Depends, FastAPI, Request
 from fastapi.middleware.cors import CORSMiddleware
 from fastapi.responses import JSONResponse
 from app.api.dashboard import router as dashboard_router
@@ -21,11 +22,20 @@ from app.api.account import router as account_router
 from app.api.importer import router as importer_router, public_router as importer_public_router
 from app.api.xirr import router as xirr_router
 from app.api.performance import router as performance_router
 from app.api.export import router as export_router
 
-app = FastAPI(title="Investment Observability API")
+
+@asynccontextmanager
+async def lifespan(app: FastAPI):
+    # Schema is managed by Alembic — run `alembic upgrade head` on deploy, not here.
+    if settings.scheduler_enabled:
+        start_scheduler()
+    yield
+
+
+app = FastAPI(title="Investment Observability API", lifespan=lifespan)
 
 
 app.add_middleware(
     CORSMiddleware,
     allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
@@ -58,17 +68,10 @@ async def log_unhandled(request: Request, exc: Exception):
         type=type(exc).__name__, msg=redact(str(exc)),
     )
     return JSONResponse(status_code=500, content={"detail": "Internal server error"})
 
 
-@app.on_event("startup")
-async def startup():
-    # Schema is managed by Alembic — run `alembic upgrade head` on deploy, not here.
-    if settings.scheduler_enabled:
-        start_scheduler()
-
-
 @app.get("/health")
 async def health():
     return {"status": "ok"}
```


---

## Your QA Task

Review the **actual code** and **actual test results** above. Do not trust the implementation notes — verify against the code and test output directly.

For each item in the approved planning spec:
1. Confirm it exists in the actual code (cite file + line if possible)
2. Confirm tests cover it (reference the test output)
3. Flag anything promised in the spec but missing or wrong in the code

Specifically check:
- All required endpoints exist and are registered in main.py
- Auth enforcement is present (not just claimed)
- All QA-required test cases are present in the test file and **passed** in the test output
- Any test failures or errors — explain what broke and why
- Edge cases the spec required — are they actually handled in the code?

If tests failed, that is a **blocker** — state clearly what failed and what needs to be fixed.

Output a structured report: what passed, what failed, what is missing. Be adversarial — assume the implementation may be incomplete until the code proves otherwise.
