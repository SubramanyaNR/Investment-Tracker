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
## Review: feature-016 — Automated Local Backups (Daily)

**Lenses applied: PM / Investor Advisor / CTO / Architect / Eng Lead / QA / Security**

### Overall assessment
Sound, well-scoped, and honestly diagnosed. The write-up correctly identifies that both pre-existing scripts are broken (not just "which one to pick"), and the `docker exec pg_dump` approach is the right call — it avoids the SSL mismatch and cross-container-networking problem in one move, and matches the verification pattern already established during feature-017. Recommend approving with the additions below folded into the plan before build starts.

### Things that check out
- **Local-only, no offsite**: reasonable for current stage (near-empty DB, no paying users yet). The reasoning that this now protects the *only* copy of data (post-Supabase-cutover) rather than a second copy is the right framing and should carry into the runbook language so future-you doesn't assume there's an implicit offsite safety net.
- **Retention reconsideration**: correct to question the inherited "7" rather than carry it by inertia — data size is genuinely trivial here, so 30 days at near-zero cost is a reasonable target. Suggest just picking a number in this planning step rather than leaving it open into implementation.
- **Restore-test-required against sandbox, never live**: good discipline, matches the project's existing safe-db-op pattern.
- **Failure visibility via log + lightweight check**: proportionate — an alerting pipeline would be over-engineering for a single-user tool.

### Gaps to close before/during implementation

1. **Credentials handling in the `pg_dump` command.** The proposed `docker exec ... pg_dump -U investment_admin investment_tracker` needs a password source — don't hardcode it in the cron entry or script. Use `.pgpass` inside the container or `PGPASSWORD` sourced from an env file with restrictive permissions (600), not inline in crontab (crontab contents are often world-readable via `/var/spool/cron`).

2. **Backup file permissions & at-rest exposure.** These dumps contain real financial holdings — treat the backup directory like the DB itself: restrict to the owning user (`chmod 700` dir, `600` files), not group/world-readable. Worth a line in the runbook given "investor trust / data accuracy" is an explicit review lens here.

3. **"Ran" vs "usable" verification.** A scheduled backup exiting 0 doesn't guarantee a restorable dump — gzip corruption or a truncated pg_dump (e.g., disk full mid-write) can still produce a file that looks fine. Cheapest guard: check the dump is non-trivially sized and that `gzip -t` passes as part of the daily job, not just cron exit-code logging. The one-time restore test validates the *procedure*; it doesn't validate *tonight's* file.

4. **Retention-cleanup blast radius.** Whatever prunes old backups (find -mtime +N -delete, typically) should be scoped tightly to the backup directory and naming pattern — a scripting slip here is a self-inflicted data-loss bug in a feature whose entire purpose is preventing data loss. Worth an explicit path/glob sanity check in the script itself.

5. **Disk space is shared with the live DB.** Local-only backups sitting on the same disk as `investment_tracker_postgres`'s data directory doesn't just fail to survive whole-disk loss (already flagged) — an unbounded or misconfigured backup directory could also fill the disk and take the live DB down with it. Low risk given the size estimates here, but worth one line in the runbook as a known limitation, not just "offsite is deferred."

6. **Decide now: fix in place vs. new script.** The request leaves "planning's call" open on whether to repair `make backup`/`backup.sh` or write a new script. Recommend: retire `backup.sh` (never worked, wrong service name/user/db — no salvageable logic) and rewrite the `make backup` target to shell out to `docker exec`, since it's the entry point already muscle-memoried into the team's workflow (matches feature-017's own pattern of preferring `docker exec` for container-scoped operations).

### Governance
Correctly flagged as requiring CEO approval (infra change to how live data is protected), and the request states the founder's message constitutes that approval for the described scope. That's consistent with `CLAUDE.md`'s gating rules — no objection, provided implementation doesn't silently expand beyond what's described here (e.g., no auto-added offsite step, no schema/script changes to the sandbox itself).

### Verdict
Approve to proceed to implementation planning, with items 1–4 above treated as in-scope hardening of *this* task (they're direct correctness/security properties of "a backup that works," not adjacent scope creep) and items 5–6 resolved as explicit decisions during planning rather than left implicit.
