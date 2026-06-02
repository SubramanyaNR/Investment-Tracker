---
description: Create + apply an Alembic migration. Usage: /migrate <message>
---

Run `make migrate m="$ARGUMENTS"` from the repo root. This autogenerates a migration from `backend/app/db/models.py`, applies it, and shows the current revision. Never hand-write SQL and never edit existing migration files. Confirm and report the new revision id.
