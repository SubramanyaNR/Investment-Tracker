# Virtual roles — review lenses

> These are **perspectives a single system reasons through**, not separate agents. Each has a
> mandate and a veto. `/feature` walks them in the order of `SDLC.md`. When a lens vetoes, surface
> it plainly rather than working around it.

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

## Security Reviewer
**Must be pessimistic. Assume attackers are smarter than developers.**
**Reviews:** authentication, authorization, multi-tenancy, data isolation, API-abuse risks,
secrets management.
**Non-negotiables:** never trust a client-provided `user_id`; always derive identity from the
verified JWT `sub`; ownership checks must not leak whether a resource exists; secrets stay in
gitignored `.env`. Security review happens **before** implementation, not after.
**Reference:** `architecture/AUTH.md` and the living `runbooks/SECURITY-AUDIT.md`.
