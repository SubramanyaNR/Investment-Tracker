---
description: Check the status of an AI-SDLC workflow. Usage: /status <workflow_id>
---
You are checking the status of an AI-SDLC workflow.

Workflow ID: $ARGUMENTS

Run `python3 .ai-sdlc/router.py status $ARGUMENTS` and present the results clearly:

- Workflow ID
- Workflow type
- Current stage
- Approval state
- Overall status

If the workflow is at a human gate (approval / manual_validation / release_approval), remind the user what action is needed to proceed.
If the workflow is at an auto-pipeline stage that hasn't been run yet, suggest running `/approve $ARGUMENTS`.
