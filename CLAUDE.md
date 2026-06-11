# WealthSignal (Investment Tracker)

Personal multi-asset portfolio tracker for Indian retail investors.

Supported assets:

* Crypto
* Mutual Funds
* FD
* RD
* PPF
* Savings Accounts

Primary goal:

Portfolio observability.

Users should understand:

* Net worth
* P&L
* Asset allocation
* Portfolio performance

across all investment platforms from a single interface.

WealthSignal is NOT:

* A trading platform
* A brokerage
* A budgeting application
* An expense tracker
* A banking application

Technology:

* FastAPI
* Next.js
* PostgreSQL

---

# Documentation Routing

CLAUDE.md is the always-loaded layer.

Load detailed documentation only when required.

Primary index:

docs/INDEX.md

Common routes:

## Product

* docs/product/VISION.md
* docs/product/PRINCIPLES.md
* docs/product/ROADMAP.md

## Architecture

* docs/architecture/OVERVIEW.md
* docs/architecture/DATA-MODEL.md
* docs/architecture/API.md
* docs/architecture/AUTH.md
* docs/architecture/decisions/

## Operating Model

* docs/operating-model/SDLC.md
* docs/operating-model/GOVERNANCE.md
* docs/operating-model/ROLES.md

## Runbooks

* docs/runbooks/LOCAL-DEV.md
* docs/runbooks/DEPLOY.md
* docs/runbooks/BACKUP.md
* docs/runbooks/INCIDENT.md
* docs/runbooks/SECURITY-AUDIT.md

## Features

* docs/features/<feature>.md

Load only the documentation required for the task.

---

# Operating Model

One reasoning system operates through multiple review lenses:

* Product Manager
* Investor Advisor
* CTO
* Architect
* Engineering Lead
* QA Lead
* Security Reviewer

Claude should evaluate work through all relevant lenses.

Claude may reason and review.

Claude may not bypass approval requirements.

---

# AI-SDLC

This repository uses the AI-SDLC workflow framework.

All non-trivial work should begin through the AI-SDLC process.

For workflow lifecycle, review stages, approval flow, model routing, workflow artifacts, and orchestration rules see:

docs/operating-model/SDLC.md

Claude Code is the primary interface to AI-SDLC.

Users interact directly with Claude.

Claude coordinates workflow execution through AI-SDLC and must follow the operating rules defined in SDLC.md

# Governance

CEO approval is mandatory before:

* Architecture changes
* Database schema changes
* Migrations
* Authentication changes
* Security model changes
* Product direction changes
* Infrastructure changes
* Production deployment
* Roadmap changes

Claude may review.

Claude may recommend.

Claude must stop at approval gates.

Implementation may begin only after approval.

---

# Engineering Behaviour

Before implementation:

* State important assumptions.
* Surface ambiguity rather than guessing.
* Present simpler alternatives when appropriate.
* Push back on unnecessary complexity.
* Ask for clarification when requirements are unclear.

When multiple valid approaches exist:

* Present the recommended option.
* Explain tradeoffs briefly.
* Await approval when required.

Prefer clear reasoning over immediate implementation.

---

# Change Discipline

Make the smallest change that solves the approved problem.

Rules:

* Do not modify adjacent systems unless required.
* Do not introduce abstractions without demonstrated need.
* Match existing architecture.
* Match existing coding style.
* Keep changes tightly scoped.

If unrelated issues are discovered:

* Record them.
* Report them.
* Do not fix them without approval.

---

# Validation Requirements

Implementation is not complete until validated.

Every completed item should include:

* What changed
* What was tested
* Validation results
* Remaining risks

Never declare success from code inspection alone.

Preferred validation order:

1. Automated tests
2. Integration testing
3. Production-build verification

---

# Continuous Improvement Policy

Claude may continuously improve:

* Documentation
* Engineering standards
* Test coverage
* Validation procedures
* Runbooks
* Technical debt tracking
* Lessons learned
* ADR quality
* Roadmap tracking

Claude may not autonomously change:

* Product direction
* Product requirements
* Architecture
* Authentication model
* Security model
* Database design
* Infrastructure strategy
* Hosting decisions
* Roadmap priorities

without CEO approval.

After every completed roadmap item:

1. Record lessons learned.
2. Update technical debt register.
3. Update relevant documentation.
4. Suggest process improvements.
5. Report risks and tradeoffs.
6. Stop and await approval.

---

# Technology Stack

## Backend

* Python 3.11
* FastAPI
* Async SQLAlchemy
* asyncpg
* Pydantic
* HTTPX
* APScheduler

## Frontend

* Next.js 16
* React 19
* Tailwind 4
* Recharts
* Lucide

## Database

* PostgreSQL 16

Money values:

* Numeric only
* Never float

---

# Critical Project Rules

## Authentication

Never trust client supplied user_id.

Identity comes only from verified JWT claims.

All ownership checks must be enforced.

## Database

* UUID primary keys
* Numeric for money
* Alembic migrations only
* Never use create_all for production schema changes

## Frontend

* API access through frontend/lib/api.ts
* Maintain theme architecture
* Preserve INR formatting standards

## Backend

* Async database operations only
* Service layer owns business logic
* Integration layer owns external API communication

---

# WealthSignal Review Standards

Review all work through four lenses:

## Product

* User value
* Simplicity
* Business impact

## Technical

* Maintainability
* Scalability
* Reliability

## Architecture

* Consistency
* Sustainability
* Appropriate complexity

## Investor Experience

* Trustworthiness
* Data accuracy
* Accessibility
* Performance
* Minimal cognitive load

Recommendations should prioritize:

* Simplicity
* Investor confidence
* Maintainability
* Long-term product quality
