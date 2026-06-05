# Governance — approval, lanes, decision trail

> The founder is the **CEO**. All critical product, architectural, and business decisions require
> explicit CEO approval. This doc defines what is gated, what is free, and how decisions are recorded.

## Gated — requires explicit CEO "approved" before execution

A change is **gated** if it affects any of:
- **Architecture** (service boundaries, new components, cross-cutting patterns)
- **Data model** (new/changed columns or tables, any Alembic migration)
- **Authentication** (`backend/app/core/auth.py`, token handling, login/session)
- **Security** posture (RLS, roles, rate limiting, secrets, CORS)
- **Product direction** (new feature, scope change, pricing, positioning)
- **Infrastructure** (Docker, deploy, env vars, external services, schedulers)
- **Production deployment**

For gated work: run `/feature` → present SDLC Steps 1–5 → **STOP at the gate** → implement only the
approved scope after the CEO says "approved".

### Enforcement
A `PreToolUse` hook (`.claude/hooks/gate.sh`) blocks `Edit`/`Write`/`MultiEdit` to gated code paths
and `make migrate` unless an approval marker exists for the current feature. The `/feature` command
writes that marker only after the CEO approves. Markers expire (12h) so a stale approval can't
silently re-authorize later work. See "Gate mechanics" below.

**Gated code paths:** `backend/app/**`, `backend/alembic/versions/**`, `frontend/app/**`,
`frontend/components/**`, `frontend/lib/**`, `docker-compose.yml`, `Makefile`,
`frontend/next.config.ts`, `backend/app/core/config.py`.

## Free lane — proceed without a gate (state when used)

To preserve solo-founder velocity, these do **not** need a gate:
- Documentation (`docs/**`, `*.md`, `.claude/**`)
- Tests (adding/fixing tests — `backend/tests/**`, `*.test.*`)
- Copy / UI-text polish *within already-approved scope*
- Formatting, comments, non-schema-touching bugfixes the CEO has asked for

If a "free-lane" change starts touching a gated concern, it becomes gated — stop and run `/feature`.

## Gate mechanics
- Approval marker: `.claude/state/feature-approved` (gitignored). Written by `/feature` on approval;
  records the approved scope + timestamp; expires after 12h.
- Emergency override: `touch .claude/state/OVERRIDE` disables the gate until removed — use only for
  deliberate free-lane code work, and remove it after.
- The hook never blocks docs/`.claude` edits, so the operating model itself stays editable.

## Decision trail
- **Architecture Decision Records:** significant or hard-to-reverse technical choices get a short
  ADR in `architecture/decisions/NNNN-title.md` (scaffold with `/adr`). One decision per file.
- **Security decisions / findings:** tracked in `runbooks/SECURITY-AUDIT.md`'s remediation backlog.
- **Product decisions:** captured in `product/ROADMAP.md` and, for guardrails, `product/PRINCIPLES.md`.

## Branch strategy
`master` = stable/deployable. Prefer a feature branch + PR. Push to `master` **only** when the CEO
explicitly asks. Never commit `.env`, `.venv/`, `__pycache__/`, `.pyc`, or `.claude/state/`.
