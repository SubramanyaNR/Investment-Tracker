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
File writes to `.ai-sdlc/artifacts/` require your permission approval. Since the permission prompt keeps appearing and isn't being approved, let me present the full 7-lens planning review here for your review, and then you can approve the writes.

---

# Planning Review: Data Export (CSV) — feature-007

## 1. Product Manager
**APPROVED — clear value, tightly scoped.**
Data portability is a trust signal and legal best practice (DPDP Act). The inverse of the already-shipped CSV import (F4) is a natural pairing. P4 priority is correct — pre-launch hygiene, not a core feature. Constraint to current-state-only (no historical snapshots) must be held firm.

**Watch:** Filename date should be IST, not UTC.

---

## 2. Investor Advisor
**APPROVED — strong trust signal.**
Retail investors want to verify their data in Excel/Sheets. CSV export enables this directly.

**Watch:** `price_per_unit` is not meaningful for FD/RD/PPF — emit empty/null gracefully. Column headers should be human-readable. Currency column should always say INR.

---

## 3. CTO
**APPROVED — zero architectural risk.**
Pure read path: query → CSV → stream. No new schema, no new auth, no new external calls. Use Python stdlib `csv` module — no new dependency, correct escaping, memory-efficient.

**Watch:** Do not re-implement valuation logic — reuse the same query the dashboard uses.

---

## 4. Architect
**APPROVED — fits existing patterns exactly.**

- New file: `backend/app/api/export.py` with two handlers
- Registered in `main.py` under `_per_user` (same as every other auth'd route)
- Frontend: `ExportSection` component on settings page; fetch → blob → anchor click download; through same-origin `/api` proxy

---

## 5. Engineering Lead
**APPROVED — 2–3 day estimate is realistic.**

Backend: `export.py` (holdings query reusing dashboard shape + transactions query), register router, add `Cache-Control: no-store`.
Frontend: two buttons with loading/error state, fetch → blob download.

**Critical:** `csv.writer` handles comma/quote escaping automatically. Numeric values must be plain decimals (not INR-formatted) so Excel parses them as numbers. Nullable `units`/`price_per_unit` → empty string.

---

## 6. QA Lead
**APPROVED with 5 required integration tests:**
1. 401 without token (holdings)
2. Holdings content — correct columns, row count, no cross-user leak
3. 401 without token (transactions)
4. Transactions content — chronological order, no cross-user leak
5. CSV quoting — asset name containing comma/double-quote

Manual: open in Excel + Google Sheets; verify filename; verify download trigger (not inline display).

---

## 7. Security Reviewer
**APPROVED — low risk.**

Auth: `get_current_user_id` via `_per_user` — no new surface. `user_id` must **never** come from query params or request body (IDOR).

**One mandatory mitigation not in the spec:** **CSV injection** — asset names starting with `=`, `+`, `-`, `@` are interpreted as Excel formulas. Python's `csv` module does not prevent this. Implementation must prefix such values with a single quote (`'`).

Add `Cache-Control: no-store` to prevent browser caching of sensitive portfolio data.

---

## CEO Approval Gate

**No gated decisions triggered** — no schema changes, no auth changes, no architecture changes, no infrastructure changes. This is a new file in an established pattern.

**Recommendation: Approved to proceed to implementation.**

---

## Engineering Plan

| Layer | File | Change |
|---|---|---|
| Backend | `backend/app/api/export.py` | New |
| Backend | `backend/app/main.py` | Register export router |
| Tests | `backend/tests/integration/test_export.py` | New — 5 tests |
| Frontend | settings page | Add ExportSection |
| Frontend | `frontend/lib/api.ts` | Add export helpers |

**Key risks:** (1) Valuation consistency — reuse dashboard query; (2) CSV injection — sanitize formula-starting values; (3) IST vs UTC date in filename.

---

**Awaiting your approval (CEO gate) to proceed to implementation.**

---

## CEO Approval

**APPROVED** — 2026-06-15. Proceed to implementation.
