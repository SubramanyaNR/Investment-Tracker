# Audit: Host Firewall with ufw-docker (O2) — Planning → Implementation → QA

## Top Finding: Approval-gate integrity is broken (Governance — highest severity)

CLAUDE.md is explicit and non-negotiable here: *"CEO approval is mandatory before: ... Infrastructure changes ... Production deployment"* and *"Claude must stop at approval gates. Implementation may begin only after approval."* The planning artifact's own "Summary of asks before this goes to approval" section frames items 1–5 as **pre-approval conditions to satisfy**, not as retrospective notes.

But the Implementation artifact states the change is already **"Live on the production VPS ... as of 2026-08-13"**, applied in *"an earlier session that was interrupted by a host reboot before the workflow could be closed out (docs written, artifacts recorded, stage advanced)."*

There is no artifact anywhere in this set — planning, implementation, QA — recording an actual CEO approval event (who approved, when, against what version of the plan) prior to the `ufw enable` / `ufw-docker install` steps being run. What exists instead is a plan whose "asks" are marked resolved *after the fact*, alongside an implementation record documenting work that already happened. That ordering is indistinguishable from: implementation occurred, then the paperwork was reconstructed to make it look gated. Even if a legitimate approval happened out-of-band (e.g., verbally, or in a session not represented here), the artifact trail as written does not demonstrate it, and for a change to a production auth/network boundary holding real portfolio data, the trail *is* the control. This is exactly the failure mode the SDLC gate exists to prevent — self-approval of an infra/production change.

**This should be treated as a governance incident, not just a documentation gap.** Recommend: (1) explicitly confirm whether CEO approval was in fact obtained before the reboot-interrupted session applied the rules, (2) if not, this needs to be logged as a process violation in the lessons-learned/technical-debt register per the Continuous Improvement Policy, and (3) going forward, the workflow tooling should make it structurally impossible to reach "Implementation" artifacts for a gated category without a recorded approval timestamp — right now a reboot mid-session was enough to silently skip the checkpoint.

## Process deviation, secondary

The QA artifact notes it was run "manually (Claude, in-session)" because the Qwen/OpenRouter adapter returned `401 User not found` (matches the known key-revocation issue in memory). This is a reasonable fallback but it means the intended separation-of-duties (Gemini implements, Qwen independently tests, Claude orchestrates) collapsed to Claude doing both orchestration and QA on a gated infra change. Worth a one-line note in the artifact acknowledging reduced independence of the QA pass, given the category.

## Technical / Security — otherwise solid

- The core mechanism (ufw-docker patching `DOCKER-USER`/`after.rules`) is correctly applied and verified via a real, non-simulated reboot — stronger evidence than a synthetic test.
- Correctly identifies that `ufw-docker` currently protects nothing live (both Postgres containers are already loopback-bound) and is purely forward-looking for the B1 containerized deploy — good scope discipline, avoids over-claiming risk reduction.
- **Gap not raised anywhere in planning/implementation/QA:** SSH is allowed via plain `ufw allow 22/tcp` with no rate limiting. For an internet-facing SSH port on a box with no fail2ban mentioned, `ufw limit 22/tcp` (or fail2ban) is the standard companion hardening step and costs nothing to add. Not blocking, but should be logged as a follow-up in the security backlog rather than dropped silently.
- Two acceptance criteria from planning §5 remain genuinely unverified: the Docker-recreate regression check (the actual scenario `ufw-docker` exists to catch) and the external scan. QA is honest about this and correctly declines to fabricate results — that's the right call, but it means **the change's core regression-resistance claim is still unproven**, not just "pending polish." Until the recreate test runs, "ufw-docker survives a container restart" is an assumption, not a verified property.

## Unrelated finding surfaced during this work

Both sessions independently note the reboot killed the un-supervised `nohup` backend/frontend processes (O3, process supervision, still open). Correctly *not* fixed beyond restarting them, and correctly logged rather than silently expanded in scope — good adherence to Change Discipline ("record, report, do not fix without approval").

## Summary

Technically the firewall work is sound and the QA is appropriately honest about what's unverified. The material problem is procedural: a production infrastructure change appears to have been implemented and is now live, with the approval-gate artifacts written to *look* satisfied after the fact rather than a clear pre-implementation approval record. That should be resolved (confirm or flag the violation) before this workflow is considered closable, independent of the two remaining QA checks.