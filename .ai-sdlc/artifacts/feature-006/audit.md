I have all the information needed. Here is the formal audit.

---

# Audit: feature-007 — Data Export (CSV)

**Auditor:** Claude (Security + Engineering lens)
**Date:** 2026-06-15
**Scope:** `backend/app/api/export.py`, `backend/tests/integration/test_export.py`, `frontend/lib/api.ts` (export helpers), `frontend/app/page.tsx` (Settings tab)

---

## Confirmed Correct

| Requirement | Status | Evidence |
|---|---|---|
| Auth via `_per_user` / `get_current_user_id` | ✅ | `main.py:92`, `export.py:31` |
| `user_id` never from query params | ✅ | All queries filter on JWT-derived `user_id` |
| `user_id` filter on all DB queries | ✅ | `export.py:39, 129` |
| `Cache-Control: no-store` | ✅ | Both handlers |
| IST filename timestamp | ✅ | `ZoneInfo("Asia/Kolkata")`, `export.py:16` |
| `csv.writer` quoting (comma/double-quote safety) | ✅ | stdlib handles escaping |
| CSV injection mitigation on asset name | ✅ | `sanitize_csv_value` prefixes `=`/`+`/`-`/`@` with `'` |
| Numeric values as plain decimals (not INR-formatted) | ✅ | Raw `Decimal` passed to writer |
| `price_per_unit` → empty string for FD/RD/PPF | ✅ | `None`-guard on `export.py:103, 153` |
| 5 required integration tests present | ✅ | `test_export.py` |
| Negative P&L Decimal not misclassified by sanitizer | ✅ | `isinstance` guard fires first, skips string path |

---

## Findings

### F1 — BUG: Transaction sort is descending, not chronological
**File:** `export.py:131`
**Severity:** Low

```python
.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
```

The approved plan, QA requirement, and UI tooltip all say "chronological order" (oldest first). `desc()` is most-recent-first — the opposite. The integration test seeds only one transaction and does not validate order, so this was not caught.

**Fix:** Change to `.order_by(Transaction.transaction_date.asc(), Transaction.id.asc())`.

---

### F2 — DEFECT: Frontend export buttons swallow errors silently
**File:** `frontend/app/page.tsx:1163, 1176`
**Severity:** Medium

```tsx
<button type="button" onClick={exportHoldings} ...>
```

`exportHoldings` / `exportTransactions` are async and throw on non-OK response, but the `onClick` handler is not wrapped. An unhandled promise rejection produces no user-visible feedback — the button appears to do nothing on failure (network error, expired token, etc.). The Engineering Lead spec required "loading/error state."

**Fix:** Wrap in a handler with `try/catch` and render an error message. A `useState` error string displayed below the button is sufficient.

---

### F3 — OBSERVATION: `sanitize_csv_value` not applied to enum fields
**File:** `export.py:97–98, 149`
**Severity:** Informational (no exploitable path)

`asset.asset_type`, `asset.category`, and `tx.transaction_type` are written raw. These are DB enum / controlled values with no user-supplied content, so there is no injection path. Not a bug, but inconsistent with the intent of the sanitizer. No action required unless the schema changes to allow free-text in these fields.

---

### F4 — OBSERVATION: Assets without valuation history silently excluded from holdings export
**File:** `export.py:48–63`
**Severity:** Informational

The holdings query uses INNER JOINs to `valuation_history`. An asset with no valuation row (e.g., just-added, pending first price refresh) is silently absent from the export. This is arguably correct but contradicts user expectation that "Export Holdings" means "all my assets." No action required now; worth a note in the feature doc.

---

### F5 — MINOR: `Content-Disposition` filename parsing is fragile
**File:** `frontend/lib/api.ts:338, 360`
**Severity:** Low

```ts
filename = disposition.split("filename=")[1].replace(/"/g, "");
```

This would break if the header ever includes `; filename*=UTF-8''...` (RFC 6266 extended form) or contains a semicolon after the filename. Current server-generated filenames (`wealthsignal_holdings_YYYYMMDD_HHMM.csv`) are safe. No action required now; a follow-up hardening pass could use a proper `Content-Disposition` parser.

---

## Test Gap

The QA5 test (`test_export_csv_injection_mitigation`) asserts `"'+Formula Asset" in content` as a raw substring check and then re-parses via `csv.DictReader`. Note that `csv.DictReader` will return the key as `'+Formula Asset` (including the quote prefix), so the test accurately verifies the mitigation end-to-end. ✅

The QA4 test (`test_export_transactions_content_and_isolation`) seeds one transaction and passes with the current descending sort. It would still pass after fixing F1. No test changes needed for the sort fix — but adding a two-transaction seed to assert ordering is recommended.

---

## Summary

| # | Finding | Severity | Action |
|---|---|---|---|
| F1 | Transaction sort descending, not chronological | Low | Fix: `asc()` |
| F2 | Export buttons have no error handling | Medium | Fix: try/catch + error state |
| F3 | Enum fields not sanitized | Informational | None |
| F4 | Zero-valuation assets silently excluded | Informational | Document |
| F5 | Fragile `Content-Disposition` parse | Low | Defer |

**F1 and F2 should be fixed before shipping.** F3–F5 are informational and can be deferred.

The security-critical requirements (auth isolation, IDOR prevention, CSV injection mitigation, cache headers) are all correctly implemented.