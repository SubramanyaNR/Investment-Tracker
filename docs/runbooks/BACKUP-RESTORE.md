# Runbook — backup & restore

> ⚠️ **No automated backups run today.** Supabase free tier has no auto-backups, and `make backup`
> is manual. Destructive DB mistakes are currently irreversible — see the `safe-db-op` skill before
> any mutating/deleting operation.

## Manual backup (run before any risky DB work)
```bash
make backup     # pg_dump → ./backups/it-<timestamp>.sql, keeps last 7
```
`make backup` reads `DATABASE_URL` from `backend/.env`, strips `+asyncpg`, and dumps via a
`postgres:17` container with `sslmode=require`. Output is gitignored (`backups/`).

## Quick app-state capture (cheap, non-DB)
For small changes, capturing API state is often enough to rebuild by hand (also in `safe-db-op`):
```bash
mkdir -p /tmp/it-snapshot
curl -s http://127.0.0.1:8000/assets            > /tmp/it-snapshot/assets.json
curl -s http://127.0.0.1:8000/transactions      > /tmp/it-snapshot/transactions.json
curl -s http://127.0.0.1:8000/valuations/latest > /tmp/it-snapshot/valuations.json
```

## Restore
```bash
psql "<DATABASE_URL without +asyncpg>?sslmode=require" < backups/it-<timestamp>.sql
```
Restore using the **admin** DSN. After restore, run `alembic upgrade head` if the dump predates the
current schema, then `make validate` and re-check a login + dashboard.

## TODO (planned, not done) — automated offsite backups
On the VPS: cron `make backup` → rclone the dump offsite (Google Drive) → periodically **test the
restore**. Tracked in `../product/ROADMAP.md` and project memory. A backup you've never restored is
a hypothesis, not a backup.
