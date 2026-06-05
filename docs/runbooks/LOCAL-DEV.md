# Runbook — local development

> Use `make`, never raw `nohup`/`pkill`. Logs: `/tmp/it-backend.log`, `/tmp/it-frontend.log`.

## Make targets
| Target | Does |
|---|---|
| `make dev` | postgres (docker) + backend on `127.0.0.1:8000` + frontend **prod build** on `:3000` |
| `make restart` | stop + rebuild + start everything |
| `make stop` | stop backend + frontend (leaves postgres running) |
| `make build` | production build of the frontend |
| `make logs` | tail both logs |
| `make validate` | health check: backend `/health` + frontend `/api/dashboard` proxy |
| `make migrate m="msg"` | alembic autogenerate → upgrade → show current (gated — see GOVERNANCE) |
| `make backup` | `pg_dump` the Supabase DB to `./backups` (keeps last 7) |

## How the app is accessed (the proxy gotcha)
The browser opens `http://172.23.80.6:3000` (the VM's IP), not localhost on the VM. The frontend
calls **same-origin `/api`**, which `frontend/next.config.ts` `rewrites()` proxies to
`http://127.0.0.1:8000`. **Never** set `NEXT_PUBLIC_API_BASE_URL` to `localhost:8000` or a hardcoded
IP — keep it `/api`. Symptom of breaking this: "Failed to load dashboard data" + empty crypto/MF
search. Rebuild the frontend after changing `frontend/.env.local` (the value is baked at build).

## Validation must use a production build
Validate against `npm run build` + `npm run start` (what `make dev`/`make build` already do), not
`npm run dev` alone.

## Post-change checklist (from SDLC.md)
1. `make build` succeeds. 2. Tests / SECURITY-AUDIT §7 matrices. 3. `make validate`. 4. Auth +
multi-tenancy intact. 5. `e2e-ui-test` skill for affected + adjacent UI. 6. Fix → repeat until clean.

## Two database connections
- `DATABASE_URL` → least-privileged **`app_user`** (RLS-enforced) — the request path.
- `ADMIN_DATABASE_URL` → **postgres** (BYPASSRLS) — migrations + scheduler only.
See `BACKUP-RESTORE.md`, `DEPLOY.md`, and `../architecture/AUTH.md`.

## Env vars (secrets in `.env`, gitignored — never commit)
- `backend/.env`: `DATABASE_URL`, `ADMIN_DATABASE_URL`, `COINGECKO_BASE_URL`, `MFAPI_BASE_URL`,
  `SCHEDULER_ENABLED`, `AI_PROVIDER` (`gemini`|`rules`), `GEMINI_API_KEY`, `GEMINI_MODEL`,
  `CORS_ORIGINS`, plus the Supabase keys for JWT verification.
- `frontend/.env.local`: `NEXT_PUBLIC_API_BASE_URL=/api` (baked at build — rebuild after changing),
  `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
