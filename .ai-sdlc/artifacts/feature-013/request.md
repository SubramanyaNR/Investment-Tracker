<!-- Artifact template: feature request -->

# Feature Request: Pagination on Holdings (GET /assets)

## User Request
`GET /assets` currently returns all holdings unbounded. The transactions endpoint already has `limit`/`offset` pagination — assets should match the same pattern.

## Endpoint Change
**Existing:** `GET /assets` — returns all assets, no pagination
**Updated:** `GET /assets?limit=N&offset=N` — paginated, with envelope response

## Requirements

### Query Parameters
- `limit` — page size, integer, 1–200, default 50
- `offset` — skip N records, integer ≥ 0, default 0
- Both optional; omitting them returns first 50 assets (not all)

### Response Envelope
Match the existing transactions response shape exactly:
```json
{
  "total": 42,
  "items": [ ...assets... ]
}
```

### Ordering
Stable sort: `asset_type` ASC then `name` ASC — deterministic across pages.

### Auth
Unchanged — `user_id` from JWT, no cross-user leakage.

### No schema changes required.

## Context
- `GET /transactions` already uses `limit`/`offset` with envelope response — reuse the same pattern
- Frontend currently calls `GET /assets` and maps the array directly — frontend needs updating to unwrap `.items`
- No new dependencies

## Acceptance Criteria
1. `GET /assets` with no params returns first 50 assets (not all)
2. `limit` and `offset` work correctly
3. `total` in response reflects full count for the user, not just current page
4. Stable sort: `asset_type` ASC, `name` ASC
5. Invalid `limit`/`offset` → 422
6. Auth enforced; cross-user isolation unchanged
7. Frontend unwraps `.items` correctly — no regressions on dashboard, holdings list
8. Integration tests cover: pagination, total count, sort order, 422 on bad params, cross-user isolation

## Estimated Effort
1–2 days (backend: 0.5 day, frontend: 0.5 day, tests: 0.5 day)
