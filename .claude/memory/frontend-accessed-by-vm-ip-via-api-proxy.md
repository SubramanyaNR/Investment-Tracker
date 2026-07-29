---
name: frontend-accessed-by-vm-ip-via-api-proxy
description: "The app is opened in a browser at http://172.23.80.6:3000 (the VM's IP), so the frontend must reach the backend via a same-origin /api proxy, never localhost:8000"
metadata: 
  node_type: memory
  type: project
  originSessionId: dbda2e20-cd6a-4ff9-91bb-5abf9f86e313
---

The user opens the UI from their own machine at **http://172.23.80.6:3000** (the VM's IP), not on the VM itself. So any `NEXT_PUBLIC_API_BASE_URL` pointing at `localhost:8000` or a hardcoded IP breaks: `localhost` resolves to the *browser's* machine, and a baked IP breaks whenever the VM IP changes (they previously committed then reverted a "hardcoded VM IP" fix for exactly this).

**Working setup (as of 2026-06-02):**
- `frontend/.env.local` → `NEXT_PUBLIC_API_BASE_URL=/api` (same-origin).
- `frontend/next.config.ts` → `async rewrites()` proxies `/api/:path*` → `http://127.0.0.1:8000/:path*`. This runs on the Next server (on the VM), which can reach the backend on localhost. No CORS, no backend exposure, no IP baked in.
- Backend stays bound to `127.0.0.1:8000` (uvicorn default) — fine, since only the Next server calls it. Frontend `next start` binds `*:3000` so the browser reaches it by IP.

**Symptom if this regresses:** "Failed to load dashboard data" + empty crypto/MF search = browser can't reach the backend API. Verify the real browser path with `curl http://172.23.80.6:3000/api/dashboard` (must return JSON, proxied).

**Note:** the `NEXT_PUBLIC_API_BASE_URL` is baked at build time, so `npm run build` must run after changing `.env.local`. For future docker-compose prod, the rewrite destination would point at the backend service name, not 127.0.0.1. Related: [[no-db-backups-exist]].
