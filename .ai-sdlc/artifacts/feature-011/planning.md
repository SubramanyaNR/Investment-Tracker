I need write permission to save the planning document. Here is the complete plan for your review — once you approve, I'll save it and advance the workflow.

---

## Feature Plan: Transaction Date Filter (feature-011)

### Summary

Add optional date-range filtering to the Transactions tab. No schema changes required — `transaction_date` is already a `Date` column on the `Transaction` model. This is a **free-lane** change: no CEO gate applies.

---

### Scope

**In:** `date_from` / `date_to` query params on `GET /transactions`, filter UI (two date inputs + Clear) in the Transactions tab header, filtered total count.

**Out:** URL persistence of filter state, filtering by asset type / transaction type, pagination UI changes.

---

### Backend — `backend/app/api/transactions.py`

Add two optional `Query` params (`date_from: Optional[date]`, `date_to: Optional[date]`). Build a `filters` list and apply conditionally to both the `COUNT` query and the `SELECT` query with `>=` / `<=` bounds. No migration needed.

---

### Frontend — 3 files

**`frontend/lib/api.ts`**
- Add `TxFilters` type (`date_from?`, `date_to?`, `limit?`, `offset?`)
- Extend `getTransactions(filters?: TxFilters)` to build a `URLSearchParams` query string

**`frontend/app/page.tsx`**
- Add `txDateFrom` / `txDateTo` state (both `""` by default)
- Extract a `fetchTransactions(dateFrom, dateTo)` callback that calls `getTransactions` with the active filter and updates `transactions` + `txTotal`
- Add a `useEffect([txDateFrom, txDateTo])` that calls `fetchTransactions` on filter change
- Add two `<input type="date">` + Clear button to the Transactions tab card header; Clear only shown when a filter is active

---

### Tests

Extend `backend/tests/integration/test_transactions.py`:
- `date_from` only, `date_to` only, both bounds, no matching transactions, cross-user isolation

---

### Risks

| Risk | Mitigation |
|---|---|
| Date format mismatch | `input[type=date]` always yields `YYYY-MM-DD`; FastAPI `date` accepts ISO |
| Race between initial load and filter `useEffect` | Filter effect only fires on filter state change, not on initial mount load |

---

**Governance: Free lane — no schema/auth/infra changes. Ready for your approval to proceed to implementation.**