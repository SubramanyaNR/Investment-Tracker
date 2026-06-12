---
description: Start a new architecture workflow using AI-SDLC. Usage: /architecture <description>
---
You are executing a new Architecture workflow via the AI-SDLC framework.

User request: $ARGUMENTS

Stages: planning → approval → implementation → qa → audit

Steps:

1. Run `python3 .ai-sdlc/router.py architecture` to create the workflow.

2. Write the user's request into `request.md`. Include: the architectural question or change, motivation, constraints, and governance concerns.

3. Run `python3 .ai-sdlc/router.py run planning <workflow_id>` to execute planning (Claude produces architecture review with all 7 lenses).

4. Present a planning summary. Architecture changes require CEO approval — stop and await explicit approval.

5. After approval: advance to `implementation` and run `python3 .ai-sdlc/router.py run implementation <workflow_id>` (Gemini executes).

Governance: all architecture changes require CEO approval before any implementation. This includes schema changes, API contract changes, service boundary changes, and infrastructure decisions.
