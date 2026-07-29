---
name: google-oauth-deferred-until-vps
description: "Google \"Continue with Google\" login is intentionally deferred until the VPS/real-domain move"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5c99eb8c-d420-4afa-8154-7244b63e2bd5
---

Google OAuth login is intentionally **deferred until the VPS deploy** (decided 2026-06-03). Email/password login works now; the "Continue with Google" button currently errors because the Google provider is not enabled in Supabase (`/auth/v1/authorize?provider=google` → 400 `provider is not enabled`).

**Why:** Google OAuth wants a real HTTPS domain; not worth configuring against the temporary `http://172.23.80.6:3000` IP.

**How to apply (at VPS time):** no code change needed — the app already calls `signInWithOAuth({provider:'google'})`. Just: (1) create a Google Cloud OAuth web client with redirect URI `https://hyuuovtkxcdupmaodwjv.supabase.co/auth/v1/callback`; (2) enable Google in Supabase → Auth → Providers with the client id/secret; (3) set Supabase Site URL + Redirect URLs to the real domain. Related: [[security-audit-and-hardening-backlog]], [[vps-deploy-todo-automated-offsite-backups]].
