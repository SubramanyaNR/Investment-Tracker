---
description: Approve the current stage of an AI-SDLC workflow and advance to the next. Usage: /approve <workflow_id>
---
You are approving an AI-SDLC workflow stage.

Workflow ID: $ARGUMENTS

Steps:

1. Run `python3 .ai-sdlc/router.py approve $ARGUMENTS`
2. Run `python3 .ai-sdlc/router.py advance $ARGUMENTS`
3. Run `python3 .ai-sdlc/router.py status $ARGUMENTS` — note the new stage name.

4. Based on the new stage, take one of three actions:

**Auto-pipeline stages** — run automatically via router, then summarize the output artifact and wait for the next `/approve`:
- `planning` → `python3 .ai-sdlc/router.py run planning $ARGUMENTS`
- `implementation` → `python3 .ai-sdlc/router.py run implementation $ARGUMENTS`
- `qa` → `python3 .ai-sdlc/router.py run qa $ARGUMENTS`
- `audit` → `python3 .ai-sdlc/router.py run audit $ARGUMENTS`

**Human gate stages** — do not auto-run; present what requires review, then wait:
- `approval` — summarize planning.md and ask CEO to review and `/approve` to proceed to implementation
- `manual_validation` — list all manual validation items from qa.md; ask user to validate in the browser and `/approve` when done
- `release_approval` — summarize audit.md findings; ask CEO for final release sign-off and `/approve` when ready to ship

**Claude-executed stages** — no router pipeline for these; Claude reads existing artifacts and executes the stage inline, writes result to the appropriate artifact file, then summarizes and waits for `/approve`:
- `triage` → read incident description, produce triage assessment, write to `incident.md`
- `fix` → read triage + planning, produce fix plan, write to `fix.md`
- `validation` → read fix, produce validation checklist, write to `validation.md`
- `rca` → read all incident artifacts, produce root cause analysis, write to `rca.md`
- `assessment` → read request, produce security threat model, write to `assessment.md`
- `remediation` → read assessment, produce remediation plan, write to `remediation.md`
- `discussion` → read request, produce structured analysis, write to `discussion.md`
- `decision` → read discussion, produce decision record, write to `decision.md`
- `release_approval` (first pass) → read all artifacts, produce release readiness report
- `release` → confirm release checklist complete, write release summary to `release.md`

Always end by stating: current stage, what was produced, and what the user needs to do next.
