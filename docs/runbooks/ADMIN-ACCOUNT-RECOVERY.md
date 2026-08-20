# Runbook — locked out of the admin account

Custom auth (architecture-002 Phase 2, `feature-017`) has no email-based password reset — there's
no mail service in a self-hosted single-user install, and none is planned. If you forget the admin
password or the login path breaks, recovery is `make reset-admin-password`, not a UI flow.

Note: login can also just be off. Check `AUTH_ENABLED` in `backend/.env` first — if it's `false`,
there's no password to forget; the app is running open by design (see `docs/architecture/AUTH.md`,
"Auth-disable toggle").

## Reset the password

Run `make reset-admin-password` — it prompts interactively for a new password
(and optionally a new email), updates the single admin row in place, and
revokes all outstanding refresh tokens. No restart needed; the change takes
effect immediately. This is now the only supported way to change admin
credentials — see `docs/architecture/AUTH.md` ("Auth-disable toggle") for why.

<details>
<summary>Manual fallback (direct DB edit, if the script can't run)</summary>

1. Generate a new bcrypt hash for the password you want:
   ```bash
   cd backend && .venv/bin/python -c "
   import bcrypt
   print(bcrypt.hashpw(b'your-new-password', bcrypt.gensalt()).decode())
   "
   ```
2. Write it into the `users` table (single row in the single-user model):
   ```bash
   docker exec investment_tracker_postgres psql -U investment_admin -d investment_tracker -c \
     "UPDATE users SET password_hash = '<hash from step 1>';"
   ```
3. Log in with the new password. No restart needed — the change takes effect immediately.

</details>

## If the `users` table is empty (bootstrap never ran, or was wiped)

Bootstrap only fires on backend startup and only if `users` is empty (see `AUTH.md`). Just restart
the backend (`make stop-backend backend`) with `ADMIN_EMAIL`/`ADMIN_PASSWORD` set in
`backend/.env` — it creates the admin row automatically, idempotently.

## If login works but you suspect a session/cookie problem instead

Revoke all outstanding refresh tokens and force a clean re-login on every device:
```bash
docker exec investment_tracker_postgres psql -U investment_admin -d investment_tracker -c \
  "UPDATE refresh_tokens SET revoked_at = now() WHERE revoked_at IS NULL;"
```
This doesn't touch the password — only forces every existing session to re-authenticate.

## Notes
- `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `backend/.env` are read once, at first-run bootstrap, and never
  again — changing them in `.env` after that has no effect (by design, so a restart can't silently
  reset the password). Use the direct DB edit above instead.
- `investment_tracker_postgres` is the real (non-sandbox) container — see
  `docker-compose.local.yml`. Don't confuse it with `investment_tracker_selfhost_postgres`, the
  disposable Phase 1 sandbox.
