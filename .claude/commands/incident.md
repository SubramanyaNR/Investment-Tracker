---
description: Start a new incident workflow using AI-SDLC. Usage: /incident <description>
---
You are executing a new Incident workflow via the AI-SDLC framework.

User request: $ARGUMENTS

Stages: triage → fix → validation → rca

Steps:

1. Run `python3 .ai-sdlc/router.py incident` to create the workflow.

2. Write the incident description into `incident.md`. Include: what is broken, when it started, who is affected, severity, and any error messages or logs available.

3. Execute `triage` inline: assess severity, identify affected components, determine blast radius, propose immediate mitigation. Write triage findings into `incident.md` under a `## Triage` section. Present and await `/approve <workflow_id>`.

4. On approval: advance to `fix`. Produce a targeted fix plan. Write to `fix.md`. Await `/approve`.

5. On approval: advance to `validation`. Produce a validation checklist confirming the fix is safe and complete. Write to `validation.md`. Await manual validation and `/approve`.

6. On approval: advance to `rca`. Produce a root cause analysis covering: timeline, contributing factors, detection gap, and preventive measures. Write to `rca.md`. Present and await `/approve`.

For production incidents: prioritise mitigation first, root cause second. Do not wait for full RCA before applying a known safe fix.
