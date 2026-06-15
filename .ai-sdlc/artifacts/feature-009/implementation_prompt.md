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
## Review: Transaction Date Filter (`GET /transactions`)

### Product (PM Lens)

Solid, well-scoped request. Date filtering is a natural and expected capability for any transaction history view — investors reviewing P&L over a tax year or comparing quarters will hit this need immediately. Keeping it backend-only for now is the right call; the frontend can consume it when a date picker is added to the UI later.

No product concerns. Approve.

---

### Investor Advisor Lens

The "inclusive on both ends" semantics are correct for investor expectations. A user asking for "Jan 1 to Jun 1" expects June 1 transactions to appear. Make sure the implementation uses `transaction_date >= from AND transaction_date <= to` (not `<`), and that this is explicitly tested. The 422 on invalid input is good — silent bad-date handling (e.g. returning empty results for a typo) would erode trust.

One thing to confirm: does `transaction_date` refer to the date of the transaction as entered by the user, or the `created_at` timestamp? If these differ (e.g. a user backfills a trade from last month), filtering on `created_at` would give surprising results. The feature request doesn't specify — this should be clarified before implementation. Recommendation: filter on `transaction_date` (the business date), not `created_at`.

---

### CTO Lens

The change is low-risk. No schema changes. No new tables. No new external dependencies. The existing pagination (`limit`/`offset`) composes cleanly with date range predicates at the SQL level.

One performance note: if the `transactions` table grows large, a query like `WHERE user_id = $1 AND transaction_date >= $2 AND transaction_date <= $3` benefits from an index on `(user_id, transaction_date)`. Worth checking whether that index already exists. If not, it should be added as part of this change — not a migration gate concern since it's non-breaking, but it should not be deferred.

---

### Architect Lens

The pattern fits existing architecture cleanly:

- Query params parsed and validated at the route layer via Pydantic (FastAPI's `Query(...)` with `date` type handles ISO 8601 parsing and produces 422 on invalid input automatically).
- `from > to` validation should be a Pydantic `model_validator` or an explicit check in the route before passing to the service layer — not buried in SQL.
- The service layer builds the filtered query; the route layer owns validation. This keeps separation of concerns intact.

Suggested validator shape:
```python
if date_from and date_to and date_from > date_to:
    raise HTTPException(422, "from must not be after to")
```

Or cleaner: a `model_validator` on a filter params model. Either works at this scale.

No architectural concerns. This is a read-path query extension, not a structural change.

---

### Engineering Lead Lens

Implementation checklist:

1. Add `from_date: date | None` and `to_date: date | None` query params (use `date` not `str` — FastAPI/Pydantic handles ISO 8601 parsing, giving 422 on bad format for free).
2. Rename to avoid shadowing Python builtins: `from` is a reserved keyword — use `from_date`/`to_date` as the Python names, aliased to `from`/`to` in the query string via `Query(alias="from")`.
3. Add cross-field validation for `from > to`.
4. Extend the service-layer query with conditional `WHERE` clauses (don't add them if the params are `None`).
5. Verify the `user_id` filter is applied before the date filter (auth first, always).
6. Check for `(user_id, transaction_date)` index; add if absent.

The alias-for-reserved-word issue (`from` → `from_date`) is the only non-obvious gotcha here. It must be addressed.

---

### QA Lead Lens

The acceptance criteria are comprehensive. Required test cases:

| Case | Expected |
|---|---|
| No filter | All user transactions, paginated |
| `from` only | Transactions on or after date |
| `to` only | Transactions on or before date |
| Both valid, ordered correctly | Transactions in range, inclusive |
| `from > to` | 422 with error message |
| Invalid date string (e.g. `2026-13-01`) | 422 |
| Results paginated correctly with filter | `limit`/`offset` applied after filter |
| Cross-user isolation | User B's transactions never appear for User A |

The cross-user isolation test is the most important one and should be an explicit integration test, not just assumed from existing tests. Suggest seeding two users' transactions with overlapping date ranges and asserting the filtered response for User A never contains User B's records.

---

### Security Lens

No new attack surface introduced. Date parameters are typed (not string-interpolated into SQL), so injection risk is nil if SQLAlchemy parameterized queries are used (they are, per existing architecture).

The only security item to verify: the `user_id` predicate must be applied regardless of whether date filters are present. There is no plausible way date filters could bypass user isolation given the architecture, but the integration test for cross-user isolation (noted above) is the verification evidence. Do not skip it.

---

### Summary

This is a clean, well-specified, low-risk backend feature. No governance gate required (no schema changes, no auth changes, no architecture changes).

**Two items to resolve before implementation begins:**

1. **Clarify filter field:** Confirm filtering applies to `transaction_date` (business date), not `created_at`. This should be stated explicitly in the implementation spec.
2. **Index check:** Verify `(user_id, transaction_date)` composite index exists; add it if not.

**One implementation gotcha to not miss:**

- Python reserved word collision: `from` must be aliased via `Query(alias="from")` on a parameter named `from_date`.

Everything else is straightforward. Estimated effort of 0.5–1 day is accurate.

---

## CEO Approval

**APPROVED** — 2026-06-15. Proceed to implementation.
