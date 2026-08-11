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

### Addendum (post-audit) — items closed
- **Orphaned `.tmp.$$` files bypass retention** (audit finding) — fixed: each run now self-heals by
  deleting any `.tmp.*` file older than a day before starting. Verified: planted a fake 2-day-old
  orphan, ran `make backup`, confirmed it was cleaned up automatically.
- **Cron log file permissions** (audit finding) — `/var/log/it-backup.log` set to `600`.
- **Encryption at rest** (audit finding) — not implemented, but no longer silent: documented
  explicitly in `BACKUP-RESTORE.md` as considered and deferred, with the conditions that would
  change the calculus (multi-user access to this VM, or an eventual move to offsite storage).
- **Code Review stage genuinely empty, not "not needed"** (audit's process finding) — accurate,
  not disputed. Flagged directly to the founder rather than silently accepted on precedent.

### Verdict
**Pass, with a real fix applied during QA, not just found and deferred.** This is exactly the value
independent QA is supposed to add — the bug wasn't visible from code review alone; it only surfaced
by actually exercising the failure path twice in quick succession.
