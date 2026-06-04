# Runbook — incident response

> Solo founder, no on-call rotation. Goal: restore service fast, avoid making it worse, write down
> what happened. **Do not** run destructive recovery (DB restore, wipes) without reading
> `BACKUP-RESTORE.md` and the `safe-db-op` skill first.

## Triage order
1. **Is it up?** `make validate` (backend `/health` + `/api` proxy). Locally `make logs` tails both.
2. **Frontend loads but no data?** Almost always the `/api` proxy / `NEXT_PUBLIC_API_BASE_URL`
   regression — see `LOCAL-DEV.md` "proxy gotcha". Symptom: "Failed to load dashboard data" + empty
   crypto/MF search.
3. **401s everywhere / can't log in?** Auth path: Supabase availability, JWKS reachability, token
   expiry, Site/Redirect URL config. JWKS failures should degrade to 401, not 500
   (`../architecture/AUTH.md`).
4. **Empty data for everyone / data appears cross-user?** STOP. Potential tenant-isolation or RLS
   issue. Check that the app connects as `app_user` and `app.current_user_id` is set per request.
   Treat as a security incident — capture state, do not mutate.
5. **External API errors (prices/NAV/insights)?** CoinGecko (30 req/min) rate limit, MFAPI, or
   Gemini. Insights fall back to rules automatically; prices may need a retry/cache (M2 open).

## Common recovery
- Bad deploy: redeploy the last known-good commit (`master` is the deployable line).
- Stuck process / port held: `make stop` then `make dev` (frees `:8000`/`:3000`).
- Schema mismatch after a change: `alembic upgrade head` via the **admin** DSN.
- Data loss suspected: `BACKUP-RESTORE.md` — but there are no automated backups yet, so prevention
  (`safe-db-op`, `make backup` before risky ops) matters more than recovery.

## After the incident
- Note timeline, cause, fix.
- If it was security/auth/tenancy → update `SECURITY-AUDIT.md` and re-run its §7 matrices.
- If a decision changed → add/supersede an ADR (`/adr`).
- If a missing guardrail let it happen → propose the fix through `/feature`.
