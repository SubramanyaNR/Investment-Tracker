# Investor Experience Review — Activation Rules & Scope

> **Conditional specialist review.** Activates for investor-facing features. Advisory only; no veto authority.
> Evaluates whether metrics, dashboards, charts, and insights are presented in a way that builds
> investor comprehension and trust. See `SDLC.md` Step 5.5 for integration into the feature review workflow.

## What is the Investor Experience Reviewer?

A specialized lens that ensures every metric, dashboard element, chart, and insight is presented
in a way that the target persona — an Indian retail investor tracking a ₹100L portfolio on a
390px phone — can **understand, trust, and act on**.

**Represents the persona:** ₹50k–₹5L/month income, uses Zerodha/Kuvera/Excel, long-term investor,
checks portfolio during market swings, needs to answer "where is my money?" and "how is it doing?"
in seconds, trusts that metrics are labeled honestly.

**Mandate:** Metric comprehension + investor trust. Not visual design, not feature discoverability.

---

## When to activate (automatic)

Activate Investor Experience Reviewer for ANY feature that includes:

### Investor-facing dashboards & metrics
- ✅ New KPI card or metric (e.g., "XIRR", "Concentration %", "Total Invested")
- ✅ New calculation or derived metric shown to investor
- ✅ Dashboard layout change (reorder KPIs, group metrics, new section)
- ✅ Changes to how an existing metric is displayed or labeled
- ✅ New financial insight or AI-generated analysis (automated insights, alerts)

### Charts & visualizations
- ✅ New chart type or data series (e.g., cost basis overlay, daily P&L, SIP performance)
- ✅ Changes to chart legend, tooltip, axis labels, or units
- ✅ Chart filtering or drill-down interactions that change investor insight

### Investor reporting & analytics
- ✅ New report type, export format, or investor-facing data table
- ✅ Portfolio analysis or performance comparison shown to investor
- ✅ Risk metric or portfolio health assessment (concentration alerts, liquidity analysis)
- ✅ New transaction history view or asset-level analytics

### Portfolio representation
- ✅ New asset type, holding model, or transaction type (e.g., manual assets, unlisted shares, ESOPs)
- ✅ Changes to how holdings are displayed, grouped, or labeled
- ✅ Mobile-specific portfolio flows or responsive changes affecting investor actions

### Information architecture
- ✅ Changes to how data is grouped, labeled, or discovered on the dashboard
- ✅ New navigation, search, or filtering for investor data
- ✅ Changes to metric terminology, naming, or abbreviations
- ✅ New documentation or glossary entries required to understand a feature

---

## When to skip (automatic skip)

Do NOT activate Investor Experience Reviewer for:

### Backend & infrastructure
- ❌ API design, service boundaries, schema design → Architect owns
- ❌ Database schema changes without investor-visible effect
- ❌ Caching, query optimization, performance tuning → Engineering owns
- ❌ Observability, logging, error tracking (unless new user-facing alert/notification)

### Security & authentication
- ❌ JWT generation, RLS policies, rate limiting (backend logic) → Security owns
- ❌ Auth middleware, session management, token handling
- ❌ OAuth provider setup, Google Sign-In backend configuration
- ❌ API abuse prevention, security hardening (backend)

### Development & operations
- ❌ Testing infrastructure, CI/CD pipelines, GitHub Actions
- ❌ Code refactoring, file reorganization, dependency upgrades
- ❌ VPS provisioning, Docker configuration, backups, monitoring
- ❌ Development tooling, Alembic migrations without investor-visible changes

### Financial calculation correctness
- ❌ Bug fixes to P&L, XIRR, or compound interest calculations → QA + Engineering own
- ❌ Edge case handling in valuation logic (math verification is QA's responsibility)
- ❌ Precision or rounding fixes in financial math
- **Note:** IER checks if the *result* is labeled honestly, not if the *algorithm* is correct.

---

## Examples

### ✅ Activate

- **F1 (Cost Basis Overlay):** New data series on chart + tooltip. Activate.
- **F2 (Price Freshness):** New "Prices updated X min ago" label on dashboard. Activate.
- **F3 (Manual Asset Tracking):** New asset type, entry form, holding display. Activate.
- **F5 (XIRR):** New KPI card on dashboard, per-asset XIRR view. Activate.
- **F6 (SIP Performance):** Per-fund XIRR, SIP-specific dashboard section. Activate.
- **"Realized vs Unrealized P&L":** Two new metric series, dashboard change. Activate.
- **"Concentration Alerts":** New alert badge, threshold explanation. Activate.
- **"Liquidity Analysis":** New data visualization, portfolio ladder view. Activate.
- **"Mobile Responsiveness Audit":** Mobile viewport, responsive breakpoints. Activate.

### ❌ Skip

- **A5 (Rate Limiting):** Backend cache + rate-limit logic. No investor-visible change. Skip.
- **A8 (Request Logging):** Backend structured logging. No UI. Skip.
- **A9 (JWKS Negative Cache):** Security optimization. No investor impact. Skip.
- **Database migration:** New column for internal use, not exposed to investor. Skip.
- **RD compound interest bug fix:** Calculation fix; QA verifies math. Skip. (IER does NOT review.)
- **Crypto price fault isolation:** Backend error handling, not investor-visible. Skip.
- **Alembic migration helper:** Developer tool, no investor-facing change. Skip.
- **GraphQL API design:** Service boundary; Architect owns. Skip.

---

## Responsibilities

### What this role produces

**Investor Experience Review report** (see example in `ROLES.md`) covering:
1. Metric comprehension — Is it self-explanatory? Are units clear?
2. Dashboard clarity — Information hierarchy correct? Can investor understand at a glance?
3. Investor trust — Does presentation build or erode confidence? Are limitations clear?
4. Presentation of insights — Is language investor-friendly? Are caveats clear?
5. Information hierarchy — Most critical data prominent? Does new element fit?
6. Mobile usability — Works on 390px? Are interactive elements usable on touch?

### What this role does NOT do

- **Visual design** (colors, typography, spacing, brand) → Engineering Lead / design system
- **Feature discoverability** (search, navigation, onboarding) → Product Manager / Architect
- **API design** (service boundaries, data model) → Architect
- **Financial calculation correctness** (algorithm verification, math edge cases) → QA Lead + Engineering Lead
- **Authentication UI** (login forms, OAuth flows) → Engineering Lead + Security Reviewer
- **Navigation structure** (menu hierarchy, routing) → Architect + Product Manager
- **Implementation plan** (file-level details, code sequence) → Engineering Lead

---

## Integration with existing roles

| Existing Role | Interaction | Orthogonal Because |
|---|---|---|
| **Product Manager** | PM defines scope + acceptance criteria (Step 1). IER evaluates implementation against those criteria (Step 5.5). | PM asks "what should we build?" IER asks "did we present it correctly?" Different concerns. |
| **Investor Advisor** | IA checks persona relevance in Step 1 ("would they use it?"). IER checks implementation quality in Step 5.5 ("can they understand it?"). | IA is coarse-grained go/no-go on feature value. IER is fine-grained feedback on execution. Complementary. |
| **Engineering Lead** | Eng Lead produces implementation plan (Step 4). IER reviews UX/comprehension of that plan. | Eng Lead says "this is how we'll code it." IER says "when investors see this, will they understand it?" IER's feedback informs code review, not the plan. |
| **QA Lead** | QA tests calculation correctness, edge cases, regressions. IER reviews how the feature is *labeled* and *presented*. | QA asks "is the XIRR calculation correct?" IER asks "is it labeled honestly?" Both needed, orthogonal. |
| **Security Reviewer** | Security owns data isolation, auth, API abuse. IER owns investor trust in the data. | Security asks "is the data safe?" IER asks "is the investor confident the data is theirs?" Different domains. |
| **Architect** | Architect owns data model, API design, service boundaries. IER reviews how the data is *presented* to investor. | Architect asks "is the schema clean?" IER asks "is the metric clear?" Orthogonal concerns. |
| **CTO** | CTO owns long-term architecture, cost, tech debt. IER owns investor comprehension. | CTO thinks "scalable system." IER thinks "can the investor trust this metric?" No overlap. |

---

## Non-negotiables

1. **Investor comprehension is not optional.** If an investor can't understand a metric in 10 seconds, it's not ready to ship.
2. **Limitations must be visible.** If XIRR excludes manual assets, the label must say so. If a price is 24 hours stale, that must be labeled.
3. **Language must be investor-friendly.** No "implementation detail," "optimization," "deprecated field." Speak investor English.
4. **Mobile-first is mandatory.** Feature works on 390px or it doesn't work. No desktop-first, mobile-as-afterthought.
5. **Trust is earned, not assumed.** Does the presentation build or erode investor confidence? If unsure, escalate to CEO.
