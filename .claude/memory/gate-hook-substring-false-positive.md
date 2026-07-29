---
name: gate-hook-substring-false-positive
description: "Low-priority backlog — the SDLC approval-gate hook substring-matches \"alembic upgrade\"/\"make migrate\" anywhere in a Bash command, incl. commit messages, causing false-positive blocks"
metadata: 
  node_type: memory
  type: project
  originSessionId: 16f72de1-a089-43c6-9a6a-9cf5ef75f940
---

The PreToolUse approval-gate hook `.claude/hooks/gate.sh` matches gated Bash by substring
(`*"make migrate"*`, `*"alembic upgrade"*`, `*"alembic revision"*`) against the **entire** command
string. So a `git commit` whose message text contains "alembic upgrade" is blocked as if it were a
real migration — a false positive (hit while committing A3b on 2026-06-04). Worked around with the
approval marker.

**Priority:** Low (engineering/process improvement; not a correctness/security issue).
**Fix idea:** match only the leading command tokens / actual invocation, or ignore heredoc bodies and
quoted message text. **Do not implement yet** — CEO deferred it for future consideration.
Related: [[operating-model-sdlc-gate]].
