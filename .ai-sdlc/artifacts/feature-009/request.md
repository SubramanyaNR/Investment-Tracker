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
