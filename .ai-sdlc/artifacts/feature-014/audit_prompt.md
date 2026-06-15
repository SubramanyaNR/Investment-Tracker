# Audit Prompt

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


## Security Context
# Security Context

Authentication & Isolation:
- Supabase Auth for token issuance.
- ES256 JWT verification in backend.
- Multi-tenancy: Every user-owned table has 'user_id' (NOT NULL).
- RLS policy: 'tenant_isolation' keyed on 'app.current_user_id' GUC.
- Ownership checks return 404 for missing or unauthorized resources.


## Investor Experience Context
# Investor Experience Context

Investor Trust & Clarity:
- Metric comprehension: Are units and calculations clear?
- Dashboard clarity: Mobile-first status at a glance.
- Investor trust: Presentation must build confidence; limitations must be clear.
- Presentation of insights: Language must be investor-friendly, not overly technical.


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

## Implementation
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

## Code Review
<!-- Artifact template: code review findings -->


## QA
### WealthSignal QA Review Report: FastAPI `on_event` → `lifespan` Migration

---

#### ✅ **Passing Items**

| **Item** | **Status** | **Details** |
|----------|------------|-------------|
| **`on_event` removal and `lifespan` implementation** | ✅ | Confirmed in `backend/app/main.py`. The `@app.on_event("startup")` logic is now encapsulated in the `lifespan` context manager. |
| **Startup logic preserved** | ✅ | `start_scheduler()` is called conditionally (`settings.scheduler_enabled`) in `lifespan`, matching the original behavior. |
| **App initialization order** | ✅ | `app = FastAPI(...)` is placed after the `lifespan` function, as required by FastAPI 0.93+ norms. |
| **Warning removal** | ✅ | No `DeprecationWarning` for `@app.on_event` appears in pytest output. The "external warnings" (Pydantic, JWT key length) are unrelated to this change. |
| **Integration test pass** | ✅ | All tests passed (`210 passed, 9 warnings`), including auth and route tests (e.g., `test_valid_token_accepted`). |
| **Middleware and routes registered** | ✅ | Middleware (CORS, exception handlers), routers (auth, dashboard, health), and endpoints (e.g., `/health`) are present and wired per `main.py`. |

---

#### ⚠️ **No Critical Failures**

- **No new errors in test output**: The pytest exit code is 0, with no test failures or errors directly attributable to this change.
- **No deprecated `on_event` warnings**: The warning about `@app.on_event` is absent from output, confirming the migration resolved the deprecation issue.

---

#### 🚨 **Missing or Suboptimal Items**

1. **Shutdown handling (if required)**
   - **Status**: ⚠️ Unclear
   - **Details**: 
     - The `lifespan` context manager currently **only contains startup logic** (`yield` is reached without post-yield shutdown logic).
     - Original `main.py` had **no `@app.on_event("shutdown")` handlers**, so this is not a regression.
     - However, the implementation should be **prepared to recognize** shutdown logic if it exists in future changes. This is **not a blocker** for this specific task.

2. **Auth enforcement in `main.py`**
   - **Status**: ⚠️ Not directly visible in code
   - **Details**:
     - Claims of auth enforcement (e.g., JWT validation) are not visible in `main.py` (likely handled via middleware in routers).
     - Tests in `test_auth_jwt.py` (e.g., `test_valid_token_accepted`) passed, implying middleware is correctly implemented **elsewhere**, but **code visibility** here is limited.
   - **Recommendation**: Verify auth enforcement code in `app/api/auth/` or middleware files.

3. **Test Coverage for Non-GUI Changes**
   - **Status**: 🟡 Suboptimal
   - **Details**: 
     - No dedicated test checks for `lifespan` behavior (e.g., scheduler startup).
     - Reliance on **indirect smoke tests** (`/health` or all-passing test suites) is acceptable for a non-functional refactor but not ideal for QA.
   - **Recommendation**: Consider adding assertions on scheduler state in the future if concerns arise.

---

#### 📌 **Edge Case Coverage**

- **No guaranteed shutdown logic**: Only applicable if `@app.on_event("shutdown")` existed before (it did not).
- **Non-relevant edge cases**: Scheduler disabled (`settings.scheduler_enabled = False`) is covered via `if` guard in `lifespan`.

---

#### 🔒 **Security Lens**

- **Auth/no auth**: No auth layer changes in this PR. Current JWT enforcement per test results works correctly.
- **New surface**: None introduced. Code only involves app lifecycle.

---

### ✅ **Conclusion**

| **Criteria** | **Verdict** |
|-------------|-------------|
| Does the code migrate `on_event` to `lifespan` correctly? | ✅ Yes |
| Are tests passing, and is the warning gone? | ✅ Yes |
| Are required endpoints and routers registered? | ✅ Yes |
| Is auth enforcement working (indirectly implied)? | ✅ Yes (based on test results) |
| Any blockers? | ❌ No |

---

**Final Verdict**: **Approve** the implementation. The code is clean, follows architecture norms, and satisfies all validating criteria. No critical flaws or missing tests to block QA sign-off.
