---
description: Start a new security workflow using AI-SDLC. Usage: /security <description>
---
You are executing a new Security workflow via the AI-SDLC framework.

User request: $ARGUMENTS

Workflow type: `secure`
Stages: assessment → remediation → validation → audit

Steps:

1. Run `python3 .ai-sdlc/router.py secure` to create the workflow.

2. Write the user's request into `request.md`. Include: the security concern, affected components, threat surface, and any known exploits or incidents.

3. Execute the `assessment` stage inline: read the request, produce a threat model covering auth, multi-tenancy isolation, API surface, data exposure, and known OWASP risks. Write to `assessment.md`. Present findings and await `/approve <workflow_id>`.

4. On approval: advance to `remediation`. Produce a remediation plan prioritised by severity. Write to `remediation.md`. Await `/approve`.

5. On approval: advance to `validation`. Produce a validation checklist. Write to `validation.md`. Await manual validation and `/approve`.

6. On approval: advance to `audit`. Run `python3 .ai-sdlc/router.py run audit <workflow_id>` (Claude audits).

Security workflows may not be bypassed regardless of urgency. Identity comes from JWT sub only. Ownership checks must not leak existence.
