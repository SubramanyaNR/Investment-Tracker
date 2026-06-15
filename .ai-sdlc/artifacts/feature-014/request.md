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
