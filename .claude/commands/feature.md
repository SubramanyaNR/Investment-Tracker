---
description: Start a new feature workflow using AI-SDLC. Usage: /feature <description>
---
You are executing a new Feature workflow via the AI-SDLC framework.

User request: $ARGUMENTS

Steps:

1. Run `python3 .ai-sdlc/router.py feature` to create the workflow and get the workflow directory path.

2. Write the user's request into `request.md` in that directory. Include full context, requirements, and any concerns stated.

3. Run `python3 .ai-sdlc/router.py run planning <workflow_id>` to execute the planning stage (Claude produces the 7-lens review).

4. Present a summary of the planning output to the user, covering: Product verdict, Architecture verdict, Security verdict, Engineering plan, QA plan, Investor Experience, and any CEO approval requirements.

5. Stop and await CEO approval. Do not proceed to implementation until the CEO explicitly approves.

After CEO approval: write the approval marker, then run `python3 .ai-sdlc/router.py approve <workflow_id>` and `python3 .ai-sdlc/router.py advance <workflow_id>` to move to `implementation`. Then run `python3 .ai-sdlc/router.py run implementation <workflow_id>` (Gemini executes).

Governance: any feature touching schema, auth, security model, or infrastructure requires explicit CEO approval before implementation may begin.
