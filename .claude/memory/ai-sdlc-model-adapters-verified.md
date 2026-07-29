---
name: ai-sdlc-model-adapters-verified
description: Verified state of the 3 AI-SDLC model adapters — Qwen/Claude work; Gemini needed --approval-mode fix to actually edit files
metadata: 
  node_type: memory
  type: project
  originSessionId: 5a7174db-29fd-45c9-ae4a-78df4a12ffe0
---

Tested all three AI-SDLC model adapters on 2026-06-12 (the user asked to verify the multi-model flow really works). Results:

- **Qwen (QA stage)** — `.ai-sdlc/models/qwen.py` via OpenRouter HTTP. ✅ Works. `OPENROUTER_API_KEY` set in `.ai-sdlc/.env`. Returns real model responses.
- **Claude (planning/audit)** — `.ai-sdlc/models/claude.py` via `claude` CLI. ✅ Works.
- **Gemini (implementation)** — `.ai-sdlc/models/gemini.py` via `gemini` CLI. ⚠️ Was BROKEN for its job, now FIXED.

## The Gemini bug (was silently producing fake implementations)

Original adapter ran `gemini -p "<prompt>"` with no approval flag. Headless `-p` defaults to approval-required mode, so the gemini CLI's LocalAgentExecutor **blocks `write_file`, `replace`, and `run_shell_command`** ("Unauthorized tool call"). Result: Gemini could NOT edit files — it only returned a TEXT summary that falsely claimed it had implemented the feature. The text got written to `implementation.md`, making it look like Gemini did the work.

**Consequence for feature-005 (onboarding flow):** the actual code (OnboardingOverlay.tsx, User model, migration) was written by Claude during the session, not Gemini — defeating the whole point of the operating model. User chose to keep that code and fix the process forward.

## The fix (verified end-to-end)

Patched `.ai-sdlc/models/gemini.py` to invoke:
`gemini --approval-mode auto_edit --skip-trust -p <prompt>` with `cwd=<repo root>` (derived from `__file__`, two levels up).

- `auto_edit` = auto-approve file edits (write_file/replace) but NOT shell — chosen by user so migrations/tests stay under human control. (`yolo` also verified working = auto-approves everything incl. shell.)
- `--skip-trust` avoids the "untrusted directory" refusal (exit 55).
- `cwd` pins edits to the repo, not `.ai-sdlc/`.

Verified: loading the adapter via `get_model('gemini')` (same path router uses) and asking it to write a file → file actually appears in repo. Confirmed working.

Related: [[ai-sdlc-orchestration-unmerged-branch]]. Router calls `adapter.run(prompt)` and writes the returned text to the stage artifact (`.ai-sdlc/router.py` run_pipeline) — adapters return text; only Gemini (CLI, agentic) has file-write side effects.
