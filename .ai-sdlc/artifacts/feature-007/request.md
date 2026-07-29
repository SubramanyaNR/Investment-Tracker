Feature Request: Data Export (CSV)

User Request:
Implement data export functionality allowing users to download their portfolio holdings and transaction history as CSV files.

Endpoints:
- GET /export/holdings.csv: Current portfolio snapshot as downloadable CSV
- GET /export/transactions.csv: Full transaction history as downloadable CSV

Holdings Export Columns: asset_name, asset_type, quantity, price_per_unit, valuation, currency
One row per holding (current state). Filename: holdings_YYYY-MM-DD.csv. Auth enforced.

Transactions Export Columns: transaction_date, asset_name, asset_type, transaction_type (BUY/SELL/DEPOSIT/WITHDRAW), amount, units, price_per_unit
All transactions chronological. Filename: transactions_YYYY-MM-DD.csv. Auth enforced.

Frontend: Add Export Data section on settings page with two download buttons (Download Holdings, Download Transactions) that trigger browser file downloads.

Context:
- Roadmap: Pre-VPS launch readiness, P4 priority (medium)
- Related: F4 (CSV import) already shipped
- Reasons: data portability (legal requirement India/EU), trust signal, Excel/Sheets integration

Scope Constraints:
- CSV format only
- Current holdings state only (no historical snapshots)
- Read-only, no data modification
- No new DB schema changes required
- No new auth model changes (middleware already enforces JWT ownership)

Acceptance Criteria:
1. Both endpoints return valid well-formed CSV (correct quoting and escaping)
2. 401 without token; user can only access their own data
3. Data matches what the user sees in the UI
4. Browser downloads work (correct filenames, open in Excel/Sheets)
5. Existing tests remain green

Estimated Effort: 2-3 days (backend: 1 day, frontend: 1 day, tests: 0.5-1 day)