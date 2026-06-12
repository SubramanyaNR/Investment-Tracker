---
description: Analysis-only discussion mode — architecture, tradeoffs, feasibility, design exploration. No workflow created. Usage: /discuss <topic>
---
You are running a discussion analysis. This is analysis-only mode.

Topic: $ARGUMENTS

Rules:
- Do NOT create a workflow.
- Do NOT invoke router.py.
- Do NOT generate implementation artifacts.
- Do NOT write to any files.
- Do NOT implement anything.

Produce a structured analysis covering:

1. **Problem / Question** — what is being explored
2. **Options** — enumerate distinct approaches (at minimum two)
3. **Tradeoffs** — for each option: benefits, costs, risks
4. **Recommendation** — which option and why, given WealthSignal's principles (simplicity, investor trust, maintainability)
5. **Open Questions** — anything requiring CEO decision or further investigation before proceeding

This is a conversation. If the user decides to proceed, they should invoke the appropriate command:
- `/feature` for product features
- `/architecture` for architectural changes
- `/security` for security concerns
- `/incident` for active issues
