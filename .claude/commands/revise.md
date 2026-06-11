---
description: Apply a revision to an existing AI-SDLC workflow without creating a new one. Usage: /revise <workflow_id> <revision description>
---
You are applying a revision to an existing AI-SDLC workflow.

Arguments: $ARGUMENTS

Parse the first word as the workflow_id. Everything after is the revision description.

Rules:
- Do NOT create a new workflow.
- Do NOT reset the workflow id.
- Preserve all existing artifact history.

Steps:

1. Run `python3 .ai-sdlc/router.py status <workflow_id>` to get current stage and status.

2. Read the relevant existing artifacts (planning.md, implementation.md, qa.md, audit.md as applicable).

3. Append the revision request to `planning.md` under a new `## Revision` section at the bottom, preserving all existing content above it. Include: what needs to change, why, and who requested it.

4. Determine re-entry stage:
   - Revision changes requirements or scope → re-enter at `planning`, stop for CEO approval before proceeding
   - Revision is an implementation fix (QA/audit/CEO identified a code issue) → re-enter at `implementation`
   - Revision is a QA-only correction → re-enter at `qa`
   - State the re-entry stage and rationale clearly before proceeding.

5. Run `python3 .ai-sdlc/router.py run <re-entry-stage> <workflow_id>` to re-execute from that stage.

6. Summarize what changed in the artifact and wait for `/approve <workflow_id>` to continue.

If re-entry requires CEO approval (scope change), stop after step 4 and do not run step 5 until approved.
