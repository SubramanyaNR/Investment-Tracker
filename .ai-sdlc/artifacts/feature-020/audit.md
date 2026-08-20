## Review: auth-toggle (feature-020 / secure-001)

### 1. Approval gate — the one blocking issue

CLAUDE.md is unambiguous: authentication and security-model changes require CEO approval *before implementation begins*, and Claude "must stop at approval gates." Project memory records the auth-disable discussion as opened 2026-08-18 with **no decision**, meant to resume 2026-08-19. Today is 2026-08-20. The planning artifact simply asserts remediation is "already approved" and puts re-litigating it out of scope — but nothing in what's shown here (planning, implementation, or QA) actually points to a recorded CEO approval, just to the existence of `secure-001/` artifacts on disk. Artifacts existing is evidence the workflow ran; it is not evidence of a decision.

This matters more than usual because the feature does something governance should care about a lot: it ships **`AUTH_ENABLED=false` as a real, working bypass of authentication**, live-tested against the production VPS holding real portfolio data. If this shipped without an actual CEO sign-off, that's not a process nicety being skipped — it's the exact scenario the gate exists to prevent.

**Action before this goes further: produce the actual approval record (who, when, what was approved) or treat this as still gated.** Everything below assumes that gets resolved.

### 2. R2 deviation — correctly escalated, needs a decision, not more debate

Dropping `token_version` in favor of refresh-token-only revocation is a reasonable engineering tradeoff (avoids a DB hit on every access-token check, bounded 15-minute exposure window, same window that already exists post-logout today). QA and planning both did the right thing by refusing to silently wave it through and instead surfacing it as a named open item. This is a good example of the operating model working as intended — don't second-guess the technical judgment, just confirm it gets an explicit CEO answer rather than defaulting to "implementer's call."

### 3. Process integrity worth naming explicitly

Both the implementation and QA stages report their assigned model adapters failing (Gemini quota, Qwen/OpenRouter 401) and Claude stepping in to do the work *and* the review of that same work directly. That collapses the intended separation between implementer and reviewer for this feature. The QA report does mitigate this somewhat by re-deriving its checklist from `validation.md` rather than trusting `implementation.md`'s narrative, which is the right instinct — but it's still one actor self-grading. Worth a line in the final report noting this as a fidelity gap in this particular run, not a clean two-model check.

### 4. Genuine strengths, no notes

- The core data-continuity test (add data while disabled → reset admin → re-enable auth → same `user_id`, data intact) was run for real against an isolated sandbox, not simulated — this was the actual load-bearing question behind the whole feature and it holds.
- Production safety was handled correctly: `AUTH_ENABLED=true` was set explicitly on the real VPS *before* restart, so the new insecure-by-default wasn't accidentally live even for a moment.
- The `conftest.py` regression (whole test suite silently running with auth disabled) was a real, easy-to-miss hole and was caught by actually running tests, not by inspection — exactly the validation discipline CLAUDE.md asks for.
- No schema/migration was introduced, keeping this within the "smaller mitigation" the R2 deviation argues for.

### 5. Minor gaps, non-blocking

- Banner never visually rendered in a real browser — low risk given the trivial conditional, but flagged consistently in both implementation and QA reports rather than glossed over. Fine to close later.
- `DEPLOYMENT_CONTEXT` unset → defaults to the stronger "hosted" wording per implementation notes — this resolves the gap the planning review raised, good outcome.

### Bottom line

Technically sound work, and the self-reporting is honest about its own deviations and gaps rather than hiding them. The one thing that needs resolving before treating this as done is procedural, not technical: **confirm an actual CEO approval exists for the auth-disable direction**, given memory shows it was undecided as of yesterday, and get an explicit answer on the R2 `token_version` tradeoff. Both are exactly the kind of decisions this governance model reserves for the CEO, not for planning/implementation/QA to assume on their own.