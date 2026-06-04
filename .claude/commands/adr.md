---
description: Scaffold a new Architecture Decision Record. Usage: /adr <decision title>
---

Create an ADR for: **$ARGUMENTS**

1. Read `docs/architecture/decisions/README.md` for the format and current index.
2. Find the next sequential number `NNNN` (look at existing `docs/architecture/decisions/*.md`).
3. Write `docs/architecture/decisions/NNNN-<kebab-title>.md` with:
   ```
   # NNNN — <Title>
   - Status: Proposed
   - Date: <today, YYYY-MM-DD>
   ## Context
   ## Decision
   ## Consequences
   ```
   Fill Context/Decision/Consequences from the conversation; keep it under a page; one decision only.
4. Add the new file to the index in `decisions/README.md`.

ADRs are documentation (free lane) — they don't need the CEO gate. But the **decision** they record,
if it's in the gated set (architecture/data-model/auth/security/infra), must have been approved via
`/feature` first. Set Status to `Accepted` only once the CEO has approved the underlying decision.
