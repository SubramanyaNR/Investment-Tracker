# Transaction Date Filter
- Shipped: 2026-06-15

## Problem & user value
Investors need to review their transaction history over specific periods (e.g., tax years, quarters, or recent weeks) to understand their P&L or allocation changes. Without filtering, users would have to manually scroll through potentially hundreds of transactions.

## How it works
The `GET /transactions` endpoint now accepts optional `from` and `to` query parameters. 
- `from`: Filters for transactions on or after this date.
- `to`: Filters for transactions on or before this date.
- The filtering is inclusive on both ends.
- Validation: If `from` is after `to`, the API returns a 422 error. Invalid date formats also return 422.

## Data & endpoints
- **Endpoints**: `GET /api/transactions?from=YYYY-MM-DD&to=YYYY-MM-DD`
- **Database**: Added a composite index `ix_transactions_user_id_transaction_date` on the `transactions` table to ensure high performance even as the transaction history grows.

## Gotchas
- **Alias**: In the Python code, these are named `from_date` and `to_date` to avoid conflict with the reserved `from` keyword, but they are aliased to `from` and `to` in the query string.
- **Inclusive**: A transaction on the exact date provided in `from` or `to` will be included in the results.

## Tests / validation
- **Integration Tests**: `backend/tests/integration/test_transactions.py`
  - Inclusive filtering for `from` and `to` independently.
  - Range filtering (both `from` and `to`).
  - Validation: 422 for `from > to`.
  - Validation: 422 for invalid date format.
  - Cross-user isolation: Verified that date filters never leak transactions from other users.
- **Performance**: Verified that the composite index is used for filtering and ordering.
