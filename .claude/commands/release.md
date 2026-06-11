---
description: Start a new release workflow using AI-SDLC. Usage: /release <description>
---
You are executing a new Release workflow via the AI-SDLC framework.

User request: $ARGUMENTS

Stages: release_approval → release

Steps:

1. Run `python3 .ai-sdlc/router.py release` to create the workflow.

2. Write the release description into `request.md`. Include: what is being released, completed feature workflow ids, open issues, deployment steps, and rollback plan.

3. Execute `release_approval` inline: produce a release readiness report covering:
   - All features included (link workflow ids)
   - Outstanding risks or known issues
   - Deployment steps
   - Rollback plan
   - Monitoring checkpoints post-deploy

   Write to `release_assessment.md`. Present and await CEO approval (`/approve <workflow_id>`).

4. On CEO approval: advance to `release` stage. Produce a release summary confirming deployment completed, write to `release.md`. Mark workflow complete with `python3 .ai-sdlc/router.py complete <workflow_id>`.

Governance: production deployment requires explicit CEO approval. No exceptions.
