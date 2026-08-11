# 0003 — RLS backstop via least-privileged app_user role

- Status: **Superseded 2026-08-10** — RLS removed entirely under the single-user model. See
  `0005-custom-auth-single-user.md` and `architecture-002`/`feature-017`. The `app_user` role
  itself is kept (least-privilege DB access is still worthwhile without RLS), only the RLS
  policies were dropped. Kept here for historical record.
- Date: 2026-06-03

## Context
Tenant isolation initially relied solely on every query carrying `WHERE user_id == sub`. Audit
finding M1: a single future missing filter would be a full-tenant breach with no second line of
defense, because the app connected as a superuser role.

## Decision
Add a database-layer backstop. The request path connects as a non-superuser **`app_user`** role
(no BYPASSRLS, no table ownership). All 8 user-owned tables enforce a `tenant_isolation` RLS policy
keyed on the `app.current_user_id` GUC, set per transaction (LOCAL, re-asserted on each BEGIN via an
`after_begin` hook). Migrations and the scheduler use a separate admin connection
(`ADMIN_DATABASE_URL`, BYPASSRLS).

## Consequences
- Two independent lines of defense: app-layer filter **and** RLS. A forgotten `WHERE` no longer
  leaks across tenants — fail-closed (no GUC → 0 rows).
- `app_user` is cluster-level (holds a password) so it is **not** created by migrations; it must be
  provisioned once per database — see `../../runbooks/DEPLOY.md` and SECURITY-AUDIT §11.
- The app-layer `WHERE user_id` filter is still mandatory; RLS is a backstop, not a replacement.
- Slight operational complexity (two DSNs, role provisioning) — accepted for the safety guarantee.
