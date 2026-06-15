# Release: feature-014 — FastAPI lifespan migration

**Released:** 2026-06-15

## What Shipped

Replaced deprecated `@app.on_event("startup")` with the modern `asynccontextmanager` lifespan pattern in `backend/app/main.py`.

| File | Change |
|---|---|
| `backend/app/main.py` | `on_event("startup")` → `@asynccontextmanager async def lifespan(app)` |

## Validation

- 210 integration tests passing
- `DeprecationWarning: on_event is deprecated` no longer appears in pytest output
- No schema, auth, or infrastructure changes

## Lessons Learned

- **Code review artifact was blank** — the router renders the template but Gemini didn't populate it. Should enforce a non-empty check or remove the stage for pure refactors.
- **Gemini attempted `run_shell_command` (blocked by gate)** — expected; validation correctly fell to QA stage.
