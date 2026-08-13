# Docs routing index

> Purpose: load **only the docs relevant to the task**, not the whole repo. `CLAUDE.md` is always
> loaded and stays lean; everything else is read on demand using the table below.

## Load-when routing

| If the task involves… | Read |
|---|---|
| **Any new feature / change of scope** | `operating-model/SDLC.md` (run the 6-step review first) |
| Knowing what needs CEO approval | `operating-model/GOVERNANCE.md` |
| The review "lenses" (CTO, PM, Security, …) | `operating-model/ROLES.md` |
| Why the system is built the way it is | `architecture/OVERVIEW.md` + `architecture/decisions/` |
| DB columns / relationships / migrations | `architecture/DATA-MODEL.md` |
| Endpoint shapes / request-response | `architecture/API.md` |
| Auth, JWT, RLS, multi-tenancy design | `architecture/AUTH.md` |
| Whether to build something / who it's for | `product/VISION.md`, `product/PRINCIPLES.md` |
| What to build next / priority | `product/ROADMAP.md` |
| Full feature backlog (all statuses, sequence, decisions) | `product/FEATURE-BACKLOG.md` |
| A specific feature's behaviour + gotchas | `features/<feature>.md` |
| Deploying to the VPS | `runbooks/DEPLOY.md` |
| Backups / restore | `runbooks/BACKUP-RESTORE.md` |
| Locked out of the admin account | `runbooks/ADMIN-ACCOUNT-RECOVERY.md` |
| Prod is broken | `runbooks/INCIDENT.md` |
| Running locally / make targets / ports | `runbooks/LOCAL-DEV.md` |
| Security posture / audit / open findings | `runbooks/SECURITY-AUDIT.md` |
| Host firewall (`ufw` / `ufw-docker`) | `runbooks/FIREWALL.md` |
| Destructive DB work | skill: `safe-db-op` |
| Validating the UI in a prod build | skill: `e2e-ui-test` |

## Tree

```
docs/
  INDEX.md                  ← you are here
  operating-model/          SDLC, roles, governance — how we decide & ship
  architecture/             the WHY + data model + API + auth; decisions/ holds ADRs
  product/                  vision, roadmap, product principles (is / is NOT)
  features/                 one file per shipped feature (problem → acceptance → gotchas)
  runbooks/                 operational procedures (deploy, backup, incident, dev, security)
```

Keep this table in sync with `CLAUDE.md` "Doc routing".
