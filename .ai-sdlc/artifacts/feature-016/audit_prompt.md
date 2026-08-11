# Audit Prompt

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


## Security Context
# Security Context

Authentication & Isolation:
- Supabase Auth for token issuance.
- ES256 JWT verification in backend.
- Multi-tenancy: Every user-owned table has 'user_id' (NOT NULL).
- RLS policy: 'tenant_isolation' keyed on 'app.current_user_id' GUC.
- Ownership checks return 404 for missing or unauthorized resources.


## Investor Experience Context
# Investor Experience Context

Investor Trust & Clarity:
- Metric comprehension: Are units and calculations clear?
- Dashboard clarity: Mobile-first status at a glance.
- Investor trust: Presentation must build confidence; limitations must be clear.
- Presentation of insights: Language must be investor-friendly, not overly technical.


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

## Implementation
## Implementation — manual, performed by Claude (2026-08-10)

Gemini's implementation run failed again (`TerminalQuotaError` — daily free-tier quota, third time
today across O4/feature-015, feature-017, and this feature). Founder directed Claude to implement
directly, same pattern as the prior two.

### What was delivered
1. **Retired `backup.sh`** — confirmed dead code, never worked against any real setup (wrong
   Compose service name, wrong DB user, wrong DB name — predates even the Supabase-era live config).
2. **Rewrote the `make backup` Makefile target** — `docker exec` into
   `investment_tracker_postgres`, `pg_dump | gzip`, no password needed (container trusts local
   Unix-socket connections). Integrity-checked every run (`gzip -t` + minimum-size sanity check,
   not just cron's exit code) — planning's item 3. `700`/`600` permissions on the backup
   directory/files — planning's item 2. Retention raised from the inherited 7 to 30 (per the
   storage-sizing discussion — negligible cost at this data volume).
3. **Daily cron entry**: `0 3 * * * make -C /opt/Investment-Tracker backup >>
   /var/log/it-backup.log 2>&1`. Verified the exact command works standalone from an arbitrary
   working directory (matching what cron actually does), not just interactively from the repo root.
4. **Restore test performed against the disposable sandbox**, not live — full round trip: backup →
   restore into `investment_tracker_selfhost_postgres` (which had been wiped back to empty during
   an unrelated incident earlier today) → verified all 12 tables present, correct row counts,
   `alembic_version` matches the live container's head exactly. Harmless `role "app_user" does not
   exist` errors during restore (that role isn't provisioned in the sandbox) — schema and data
   restored correctly regardless; documented in the runbook so a future human doesn't panic at them.
5. **`docs/runbooks/BACKUP-RESTORE.md` rewritten** to match the new mechanism, including the
   restore/dry-run procedure and the harmless-error note above.

### Credentials handling (planning item 1) — resolved more simply than anticipated
Planning assumed a `PGPASSWORD`/`.pgpass` mechanism would be needed. Tested directly: `docker exec`
into the container authenticates via the trusted local Unix socket with no password at all —
simpler and more secure than any credential-file approach (nothing to leak, nothing in `ps aux`,
nothing in a file that could be misconfigured with wrong permissions).

### Retention-cleanup blast radius (planning item 4)
The prune step (`ls -1t backups/*.sql.gz | tail -n +31 | xargs -r rm -f`) is scoped to the exact
glob pattern this script itself writes — can't touch anything outside `backups/*.sql.gz`.


## Code Review
<!-- Artifact template: code review findings -->


## QA
## QA — manual, performed by Claude (2026-08-10)

Qwen's QA run failed again — same `OpenRouter API 401: "User not found"` as `feature-017`, confirming
this is a broken/invalid key, not a transient issue. Founder directed Claude to perform QA directly,
same precedent as earlier today.

### Automated suite
92 unit + 119 integration tests, all passing — unaffected by this change as expected (pure
infra/Makefile/cron work, no Python application code touched).

### Manual verification — happy path
- `make backup` produces a valid, non-trivial gzip file with correct real SQL dump content
  (verified via `zcat | head`).
- Directory permissions `700`, file permissions `600` — confirmed via `stat`.
- Cron entry installed and independently verified to work from an arbitrary working directory via
  `make -C /opt/Investment-Tracker backup` (matches exactly what cron invokes, not just the
  interactive `cd`-first usage).
- Full restore round-trip against the disposable sandbox: all 12 tables, correct row counts,
  `alembic_version` matches the live container's migration head exactly.

### Real bug found and fixed during this QA pass
**Same-second timestamp collision destroys a prior good backup.** Reproduced directly: run a
successful `make backup`, then immediately run a failing one (simulated via a bad container name).
The failing run's `gzip > "$out"` opens/truncates the output file **the instant gzip starts**,
before the pipeline's overall success/failure is even known — if the two runs land in the same
wall-clock second (the timestamp's resolution), the second run silently destroys the first run's
completed file the moment it starts, and then its own failure-cleanup (`rm -f "$out"`) deletes it
entirely. Confirmed this is not hypothetical — it reproduced on the **first** manual re-run during
this QA pass.

Real-world risk for the intended once-daily cron use case is low (no reason to run twice in the
same second under normal operation), but it's a live landmine for anyone manually re-running the
backup (as QA itself just did), and it's exactly the kind of "a feature meant to prevent data loss
becomes a data-loss bug itself" risk Planning flagged for the retention-cleanup step specifically —
this is the same class of risk in a different part of the same script.

**Fix applied**: write to a PID-suffixed temp file (`$final.tmp.$$`) throughout, only `mv` to the
final name after all integrity checks pass. `mv` is atomic and only ever touches the exact final
filename it's given — a same-second collision can now only affect two *temp* files (which have
distinct PIDs and are cleaned up independently), never a previously-completed backup.
**Re-verified after the fix**: reproduced the exact same collision scenario — the good backup now
survives, no leftover temp files.

### Not independently re-verified (carried forward, low priority)
- Behavior under an actually-full disk (only the size/corruption checks were exercised, not a real
  ENOSPC condition) — the existing checks (gzip -t, min-size) would likely catch a
  disk-full-mid-write truncation as "suspiciously small" or "corrupt gzip," but this wasn't tested
  with a literal full disk.
- The cron job's *actual* 3am unattended firing (only the equivalent command was verified
  standalone, not a real overnight cron trigger) — reasonable to consider closed given the command
  was verified to work identically to what cron invokes, but noting the distinction.

### Verdict
**Pass, with a real fix applied during QA, not just found and deferred.** This is exactly the value
independent QA is supposed to add — the bug wasn't visible from code review alone; it only surfaced
by actually exercising the failure path twice in quick succession.

