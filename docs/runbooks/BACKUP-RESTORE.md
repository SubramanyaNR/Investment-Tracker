# Runbook — backup & restore

> ✅ **Automated daily backups run** (`feature-016`, 2026-08-10) — cron, 3am, local-only (no
> offsite). See `../product/ROADMAP.md` `O1` for the offsite decision (deferred, not forgotten).

## How it works
- `make backup` — `docker exec`s into the live Postgres container (`investment_tracker_postgres`),
  runs `pg_dump`, gzips the output to `./backups/it-<timestamp>.sql.gz`. No password needed — the
  container trusts local Unix-socket connections, so `docker exec` authenticates without a
  `PGPASSWORD` ever touching disk or a process list.
- Verified as part of every run, not just cron's exit code: `gzip -t` (catches truncation/corruption)
  and a minimum-size sanity check (catches a silently-empty dump). Either failure removes the
  partial file and exits non-zero.
- **Atomic write**: dumps to a PID-suffixed `.tmp.$$` file first, only `mv`s to the final
  `it-<timestamp>.sql.gz` name after all checks pass. Without this, two runs landing in the same
  wall-clock second would silently destroy each other's output — found and fixed during QA
  (`feature-016`), reproduced on the first manual re-run. If a run is ever killed mid-flight
  (crash, `kill -9`, power loss), a `.tmp.<pid>` file can be orphaned — each run self-heals by
  deleting any such orphan older than a day before starting.
- `backups/` is `700`, each dump file is `600`, and `/var/log/it-backup.log` (the cron log) is
  `600` — these all touch real financial data or its metadata.
- **Encryption at rest: considered, explicitly deferred, not silently skipped.** Dumps are
  plaintext SQL. `700`/`600` permissions are the accepted baseline for a single-user local box with
  no other OS-level accounts; revisit if that ever changes (shared/multi-user access to this VM) or
  if the local-only backup decision (`O1`) is ever revisited toward offsite storage, where
  in-transit/at-rest exposure changes materially.
- Retention: last 30 backups kept (≈30 days at daily cadence), older ones pruned automatically.
  Storage cost is trivial for this app's data volume (low single-digit MB even after years of use).
- Cron: `crontab -l` shows `0 3 * * * make -C /opt/Investment-Tracker backup >>
  /var/log/it-backup.log 2>&1` — check that log if a day's backup is ever in doubt.

## Manual backup (also run before any risky DB work)
```bash
make backup
```

## Quick app-state capture (cheap, non-DB)
For small changes, capturing API state is often enough to rebuild by hand (also in `safe-db-op`):
```bash
mkdir -p /tmp/it-snapshot
curl -s http://127.0.0.1:8000/assets            > /tmp/it-snapshot/assets.json
curl -s http://127.0.0.1:8000/transactions      > /tmp/it-snapshot/transactions.json
curl -s http://127.0.0.1:8000/valuations/latest > /tmp/it-snapshot/valuations.json
```

## Restore
**Never restore onto the live container without a fresh backup of its current state first** — see
`safe-db-op`. To test a restore (recommended periodically, not just once) or to actually recover:

```bash
zcat backups/it-<timestamp>.sql.gz | docker exec -i investment_tracker_postgres psql -U investment_admin -d investment_tracker
```

For a **dry-run test** (recommended — verifies the backup is real without touching live data), use
the disposable sandbox instead:
```bash
zcat backups/it-<timestamp>.sql.gz | docker exec -i investment_tracker_selfhost_postgres psql -U selfhost_user -d investment_tracker_selfhost
```
You'll see `ERROR: role "app_user" does not exist` lines if that role isn't provisioned in the
target — harmless, it only means the dump's `GRANT` statements for that role can't apply; schema
and data still restore correctly. Confirm with:
```bash
docker exec <container> psql -U <user> -d <db> -c "SELECT version_num FROM alembic_version;"
docker exec <container> psql -U <user> -d <db> -c "\dt"
```
A dump restored into the disposable sandbox leaves real (if minimal) data sitting there — wipe it
(`docker compose -p investment-tracker-selfhost -f docker-compose.selfhost.yml down -v`) before
using the sandbox for anything else.

## TODO (planned, not done) — offsite backup copy
Local-only today, by explicit founder decision (`O1`, 2026-08-10) — this VM's local Postgres
container is the *only* copy of the data, so this backup is real protection against everyday
mistakes (bad migration, accidental `DELETE`, app bug), but not against whole-disk/VM loss.
Revisit (push to another personal device over Tailscale, or cloud storage) if that residual risk
stops being acceptable. Tracked in `../product/ROADMAP.md`.
