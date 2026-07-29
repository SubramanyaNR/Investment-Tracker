---
name: no-db-backups-exist
description: No Postgres backups exist yet — backup.sh is present but has never produced a dump
metadata: 
  node_type: memory
  type: project
  originSessionId: dbda2e20-cd6a-4ff9-91bb-5abf9f86e313
---

`backend/.. /backup.sh` (repo root `backup.sh`) exists but has never been run — there is no `./backups` dir and no `.sql`/dump files anywhere. The Postgres data lives only in the Docker named volume `postgres_data`. So any destructive DB mistake is irreversible; there is nothing to restore from.

**How to apply:** Before any operation that can mutate/delete real data on the live DB, capture current state first (e.g. `curl /assets`, `/transactions`, `/valuations/latest` to a file) so you can rebuild by hand if needed. Related: [[post-assets-merges-by-scheme-or-coin]].
