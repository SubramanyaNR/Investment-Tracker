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
