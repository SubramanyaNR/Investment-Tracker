## Planning Review: Pagination on GET /assets

### Overall Assessment

This is a well-scoped, low-risk feature. The pattern is already proven in the codebase (transactions endpoint), the requirement is clear, and no schema changes are needed. The main risks are frontend regression and the behavior change to the default response shape — both manageable.

---

### Product Lens

The request is justified. Unbounded `GET /assets` is a latency and payload risk as portfolios grow. Matching the transactions pattern is the right call — consistency reduces cognitive load for both developers and API consumers.

One concern: the default changing from "all assets" to "first 50" is a silent behavior change. For current users with fewer than 50 assets this is invisible. But the API contract is changing. If there are any integrations or scripts outside the frontend that rely on `GET /assets` returning everything, they will silently truncate. This should be noted in release notes and, if the API is ever exposed externally, versioned or documented.

The 200-item upper bound on `limit` is sensible for a personal tracker. No objection there.

---

### Investor Advisor Lens

Holdings is a trust-critical surface. The investor needs to see their complete portfolio. The frontend must handle pagination correctly — if a holdings list silently shows only 50 of 80 assets, the investor's net worth view will be wrong. This is the highest-risk failure mode of this feature.

Two options for the frontend:
1. Fetch all pages sequentially and merge (preserves current "show everything" UX).
2. Add explicit UI pagination (page controls or infinite scroll).

The request as written implies option 2 (unwrap `.items`), but doesn't specify whether the frontend will fetch all pages or paginate the UI. This needs to be resolved before implementation. If the dashboard aggregates net worth from the holdings list, it must not silently use a partial page.

---

### Architect Lens

The design is sound and matches the existing pattern. A few notes:

- **Stable sort on `asset_type` ASC, `name` ASC** — good. Confirm the sort is applied at the DB layer (ORDER BY in SQL), not in application code, so it remains consistent under `LIMIT`/`OFFSET`.
- **Total count** — needs a separate `COUNT(*)` query or a window function. A naive implementation that counts `len(results)` will be wrong. Confirm the implementation uses `SELECT COUNT(*) WHERE user_id = $1` independent of the paginated query.
- **No schema changes** — confirmed, this is pure query-layer work.

The envelope shape `{"total": N, "items": [...]}` is correct and matches transactions. No objection.

---

### Engineering Lead Lens

The 0.5 / 0.5 / 0.5 day estimate is reasonable if the developer is familiar with the transactions endpoint to copy from. The main implementation tasks:

1. Backend: Add `limit: int = Query(50, ge=1, le=200)` and `offset: int = Query(0, ge=0)` to the route. Run two queries: count and paginated fetch with ORDER BY. Wrap in envelope. Pydantic will auto-validate and return 422 on bad params — no extra error handling needed.
2. Frontend: Every callsite of `GET /assets` must be updated to read `.items` instead of the raw array. Search for all usages — dashboard, holdings list, any export or allocation chart that may derive from the assets response.
3. Tests: The acceptance criteria are complete and testable. Cross-user isolation test is mandatory given the auth model.

Risk: Frontend callsite audit. Missing even one callsite produces a runtime error (mapping `.items` on an array, or vice versa). This should be caught by TypeScript if the return type is updated at the `api.ts` layer — confirm the type is updated there first so the compiler surfaces all usages.

---

### QA Lens

The acceptance criteria are well-written and cover the right cases. Additions worth considering:

- Test `limit=0` and `limit=201` → both should 422.
- Test `offset` beyond `total` → should return `{"total": N, "items": []}`, not an error.
- Test sort stability across pages: page 1 last item and page 2 first item should not overlap or skip.
- Regression: net worth total on dashboard should be unchanged after this feature ships (requires either fetching all pages or computing net worth server-side).

---

### Security Lens

Auth enforcement is unchanged — `user_id` from JWT, app-layer filter. No new attack surface from adding `limit`/`offset`. The 422 on invalid params is handled by FastAPI's Pydantic validation automatically. No concerns.

---

### CTO Lens

Approve proceeding to implementation. This is low-risk, low-complexity, and closes a real gap. The one decision that needs resolution before implementation starts:

**Does the frontend paginate the UI, or does it fetch all pages?**

For a personal tracker where most users have fewer than 50 assets, fetching all pages (with a reasonable hard cap) is simpler and preserves the existing UX with no UI work. UI pagination is more work and adds complexity the feature request doesn't ask for. I recommend: fetch all pages up to a reasonable cap (e.g., 5 pages × 200 = 1000 assets) and merge on the frontend. This keeps the UX identical while making the backend paginated. Revisit if a user ever hits that cap — unlikely for a personal tracker.

---

### Summary

**Ready to implement with one pre-implementation decision:** confirm frontend strategy (fetch-all-pages vs. UI pagination). Backend design is complete and correct. Estimated effort of 1–2 days is accurate. No governance gate required — no schema change, no auth change, no architecture change.

**Frontend decision:** Fetch all pages sequentially and merge. Cap at 5 pages × 200 = 1000 assets. Keeps existing UX identical.

---

## CEO Approval

**APPROVED** — 2026-06-15. Proceed to implementation.