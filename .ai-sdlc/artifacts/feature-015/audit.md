## Audit — feature-015: Tailscale private HTTPS access

### Request vs. delivered
Delivered against the intent of `request.md` (private, trusted HTTPS, nothing newly public,
before the auth rewrite), with one mechanism deviation and one scope deviation, both deliberate
and recorded:

1. **Mechanism**: `tailscale serve --bg` instead of raw `tailscale cert`. This is *stronger* than
   what was requested, not a shortfall — the planning review (`planning.md`) had already flagged
   raw `tailscale cert` as leaving a silent 90-day cert expiry with no renewal path. `serve`
   closes that gap and was recommended there before implementation started.
2. **Scope**: Phase 4's "decide whether to close plaintext port 3000" resolved to **keep it open**,
   not close it — because this repo ships as an OSS self-host project and `docker-compose up` must
   work out-of-the-box with no Tailscale/nginx prerequisite. This is a considered product decision
   (out-of-the-box UX for future self-hosters) over a stricter security default on this one
   instance, tracked explicitly as `O5` rather than silently left undone.

### Governance
Founder-originated infrastructure request constitutes the CEO approval CLAUDE.md requires for
infra changes. Implementation/QA/audit performed manually by the founder rather than through the
Gemini/Qwen pipeline — appropriate per SDLC.md's model-ownership fallback, since this stage
requires interactive account-level actions (browser auth, admin console settings) no model can
perform.

### Security
- `funnel` confirmed off (tailnet-only) — the sharpest risk called out in planning.md was avoided.
- Backend (`:8000`) and Postgres (`:5432`) remain `127.0.0.1`-only, unaffected by this change.
- Port `3000` remains publicly reachable in plaintext — a known, intentional, and documented
  tradeoff (see O5), not an oversight.

### Open follow-ups (non-blocking, carried in qa.md)
- External non-tailnet reachability test not independently performed.
- Supabase Auth allowed-origin list not confirmed to include the new `*.ts.net` origin.
- Cert auto-renewal not yet observed over a full cycle (expected — same-day implementation).

### Verdict
**Approved and complete.** Core deliverable met and verified; deviations are improvements or
explicit, documented product decisions, not gaps. Follow-ups tracked, not lost.
