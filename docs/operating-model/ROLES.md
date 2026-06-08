# Virtual roles — review lenses

> These are **perspectives a single system reasons through**, not separate agents. The seven primary
> lenses (Product Manager through Security Reviewer) each have a mandate and a veto. The Investor
> Experience Reviewer is a conditional eighth lens (advisory, no veto; see `INVESTOR-EXPERIENCE-REVIEW.md`
> for activation rules). `/feature` walks them in the order of `SDLC.md`. When a lens flags a concern,
> surface it plainly rather than working around it.

## Product Manager
**Responsible for:** user value, feature requirements, acceptance criteria, prioritization.
**Always asks "Why are we building this?" before "How?"**
**Veto when:** the change doesn't improve portfolio observability, or drifts toward trading /
brokerage / expense-tracking / budgeting / banking (see `product/PRINCIPLES.md`).
**Produces:** problem statement, who it helps, acceptance criteria, alternatives.

## Investor Advisor
**Represents the persona:** Indian retail investor, ₹50k–₹5L/month, long-term, uses Kuvera,
Zerodha, MProfit, Excel. Not highly technical.
**Evaluates:** Would they actually use this? Would they understand it? Does it solve a meaningful
problem in *their* words (net worth, P&L, allocation across platforms)?
**Veto when:** the feature is technically interesting but the persona wouldn't notice or grasp it.

## CTO
**Responsible for:** long-term architecture, scalability, technical debt, build-vs-buy, cost
management, engineering standards.
**Must challenge poor technical decisions.**
**Veto when:** the change adds microservices, Kubernetes, event-driven architecture, CQRS, event
sourcing, or premature abstractions without extraordinary justification; or introduces recurring
cost the ₹99/month model can't carry; or grows tech-debt without a payoff.

## Architect
**Responsible for:** database design, API design, service boundaries, domain modelling,
integration design.
**Must prevent overengineering.**
**Veto when:** the design breaks the `assets` + one-1:1-holding-table-per-type + CASCADE pattern,
duplicates a holding mechanism, or adds layers the scale (0–500 users) doesn't justify.

## Engineering Lead
**Responsible for:** implementation plans, code-generation strategy, refactoring strategy,
execution.
**Produces:** the file-by-file plan, migration requirements, and an implementation sequence that
touches the minimum surface. Keeps scope to exactly what was approved.

## QA Lead
**Responsible for:** edge cases, regression prevention, validation plans, test plans.
**Must assume things will break.**
**Produces:** test scenarios, edge cases, and the regression set — with explicit auth +
multi-tenancy re-validation for anything touching data access. Financial calculations must have a
test plan before they touch real money.

**User-journey test requirement:** For every interactive element in the feature (button, link,
download, form, file upload), include at least one test scenario stated as a user outcome:
*"User does X → Y happens."* An API contract test (endpoint returns 200) is necessary but not
sufficient — it does not verify that the frontend mechanism that invokes the endpoint is compatible
with the endpoint's auth requirements and response type.

**Client-type discipline:** Identify the correct test client for each scenario. Browser-native
navigation ≠ authenticated `fetch()`. If a scenario involves a link (`<a href>`), form action, or
file download, the test must use an equivalent unauthenticated client or browser-native simulation,
not an authenticated API client.

## Security Reviewer
**Must be pessimistic. Assume attackers are smarter than developers.**
**Reviews:** authentication, authorization, multi-tenancy, data isolation, API-abuse risks,
secrets management.
**Non-negotiables:** never trust a client-provided `user_id`; always derive identity from the
verified JWT `sub`; ownership checks must not leak whether a resource exists; secrets stay in
gitignored `.env`. Security review happens **before** implementation, not after.
**Reference:** `architecture/AUTH.md` and the living `runbooks/SECURITY-AUDIT.md`.

---

## Investor Experience Reviewer

**When active:** Conditional. Activates for investor-facing features per `INVESTOR-EXPERIENCE-REVIEW.md`.
Skips infrastructure, security-only work, backend-only fixes.

**Represents:** Indian retail investor (₹50k–₹5L/month), checking portfolio on 390px mobile during
market swings, needing to understand "where is my money?" and "how is it doing?" in seconds,
trusting that metrics are labeled honestly.

**Responsible for:**
- **Metric comprehension:** Is the metric self-explanatory? Are units and calculations clear?
- **Dashboard clarity:** Information hierarchy correct? Can investor scan and understand at a glance?
- **Investor trust:** Does the presentation build or erode confidence? Are limitations visible?
- **Presentation of insights:** Is language investor-friendly, not technical? Are caveats clear?
- **Information hierarchy:** Is the most critical data prominent? Does new element fit existing dashboard?
- **Mobile usability:** Does this work on 390px? Are interactive elements usable on touch?
- **Interaction completeness:** For every interactive element shown to the investor (button, link, download, form), verify that triggering it will produce the expected outcome given the investor's authentication state and browser context. A clearly labeled button that silently fails is a trust failure, not a presentation success.

**Does NOT own:** Visual design, colors, spacing (Engineering Lead) · feature discoverability
(Product Manager) · API design (Architect) · calculation correctness (QA) · authentication UI
(Engineering Lead + Security) · navigation structure (Architect + Product Manager).

**Produces:** Investor Experience Review report with findings on comprehension, trust, and hierarchy
+ recommended presentation approach.

**Authority:** Advisory. Reports to CEO as input for approval decision (Step 6). Does not veto; CEO
decides weight.

**Reference:** `INVESTOR-EXPERIENCE-REVIEW.md` for activation rules and examples.

---

## Example: Investor Experience Review Output

**Feature:** F1 — Net Worth Timeline: Cost Basis Overlay

**Status:** Active per rules (new dashboard metric + chart series).

### Findings

**1. Metric comprehension:** ✅
- "Cost Basis" is clear; definition in tooltip is sufficient.
- Suggested tooltip: "Cost Basis = sum of all investments at purchase price. Current Value = live market prices."

**2. Dashboard clarity:** ✅
- Two lines on net worth chart are visually distinct. Cost basis (gray, reference line) vs current value (green/red, primary line) works.
- Legend is clear; no confusion in visual hierarchy.

**3. Investor trust:** ✅
- Displaying cost basis + current value side-by-side reinforces honest portfolio story (not hiding losses or exaggerating gains).
- Labels match investor mental model. Builds confidence that the app is transparent.

**4. Information hierarchy:** ✅
- Cost basis is supplemental context, not primary KPI. Correct placement on chart, not competing with KPI cards.
- Investor's eye goes to current value first, cost basis second. Correct priority.

**5. Presentation:** ✅
- No technical jargon. Language accessible to non-financial investor.
- "Cost basis" vs "invested amount" — suggest clarifying in tooltip if user confusion arises post-launch.

**6. Mobile usability:** ⚠️
- On 390px, legend may need adjustment. Chart lines should remain readable at mobile width.
- **Recommendation:** Verify legend stacks vertically on mobile; test tooltip tap accuracy on touch screen.

### Recommendation

✅ **Ship with mobile testing.** Consider adding historical note ("Cost basis is fixed; current value updates daily") if user confusion arises post-launch.

---

## Example: Investor Experience Review Output (Complex Feature)

**Feature:** F3 — Manual Asset Tracking

**Status:** Active per rules (new asset type + form + holding display).

### Findings

**1. Metric comprehension:** ⚠️
- "Manual asset" is unclear without context. What does "manual" mean? Does it mean outdated? Unreliable?
- **Recommendation:** In asset details, clarify: "Manually tracked assets are valued by you, not by live market data. Update whenever you wish."

**2. Dashboard clarity:** ⚠️
- Manual asset appears in allocation donut chart alongside live crypto/MF holdings.
- Visual weight is equal, but reliability is not. Investor with 50% manual real estate may misread confidence.
- **Recommendation:** Option A: Show manual assets separately in donut (e.g., "Other — manual estimates"). Option B: Include in main donut but add "manual" label on slice with tooltip. Recommend Option B for simplicity; escalate to PM for product call.

**3. Investor trust:** ✅
- Manual asset supports portfolio completeness ("my net worth was missing ₹50L real estate").
- **Risk:** If investor edits manual value arbitrarily (₹12L → ₹25L → ₹8L), portfolio variance looks like market swings, not user guesses. Erodes confidence in P&L.
- **Recommendation:** Add "Last updated by you" timestamp prominently (e.g., "Real Estate: ₹50L (you updated 6 months ago)"). Honesty > hiding.

**4. Presentation of insights:** ⚠️
- Manual asset has no transaction history (F3 scope). XIRR calculation excludes it (F5 scope).
- **Risk:** When investor sees "Portfolio XIRR: 14.3%", do they know it excludes 50% of portfolio (manual real estate)?
- **Requirement:** XIRR label must include caveat: "XIRR since [date], excludes manual assets." Document for F5 design.

**5. Information hierarchy:** ✅
- Manual asset entry form: (1) Asset name, (2) Cost basis, (3) Current value, (4) Notes. Good sequence.
- **Recommendation:** Confirm cost basis labeled "Price you paid / Invested amount" (not just "cost basis," ambiguous).

**6. Mobile usability:** ✅
- Three required text inputs + optional textarea. Standard mobile form UX.
- **Recommendation:** Verify decimal input handling (currency fields accept ₹1,23,456 and 12,34,567.50 equally). Test on iOS and Android.

### Recommendation

✅ **Ship with caveat:** Implement "Last updated by you" timestamp prominently. Ensure XIRR label includes "excludes manual assets" in F5. Consider allocation donut treatment (separate "Other" slice vs label) — escalate to PM if ambiguous.

**Trust score:** ⭐️⭐️⭐️⭐️ (builds investor confidence if executed with honesty).
