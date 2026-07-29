---
name: vps-deploy-todo-automated-offsite-backups
description: "VPS-day task — set up automated + offsite backups, because Supabase free tier has no managed backups and `make backup` is manual + local-only"
metadata: 
  node_type: memory
  type: project
  originSessionId: dbda2e20-cd6a-4ff9-91bb-5abf9f86e313
---

The DB lives on **Supabase (managed Postgres, Singapore region)**. The data itself is durable on Supabase, but:
- Supabase **free tier has no automatic backups** (Pro $25 adds daily/PITR).
- The `make backup` target (pg_dump → `./backups/`, keeps last 7) is **manual and local-only** — files land on whatever box runs it.

**Defer to VPS deploy (Phase 3), do NOT bother on the throwaway dev VM** (its local backups vanish with the VM):
1. **Cron** nightly `make backup` on the VPS.
2. **rclone** copy each dump offsite (Google Drive / S3) — needs one-time rclone config.
3. **Test a restore** into a scratch DB to prove the backups actually work.

Until then, run `make backup` manually before anything risky (see [[no-db-backups-exist]] — now superseded by Supabase, but the discipline stands). Related: [[frontend-accessed-by-vm-ip-via-api-proxy]].
