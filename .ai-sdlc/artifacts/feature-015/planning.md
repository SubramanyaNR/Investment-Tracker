# Review: Tailscale Private HTTPS Access (O4)

## Overall
Sound, well-scoped request with real technical justification (Secure-cookie prep for the auth rewrite) and correct governance framing. A few technical gaps in the requirements could cause either implementation friction or a violation of the "nothing new exposed publicly" constraint if not addressed before work starts.

## Architecture / Eng Lead — the biggest gap: unspecified serving mechanism
The request says "use `tailscale cert`" and separately "serve the app... over HTTPS via this cert," but doesn't specify *how* Next.js/FastAPI actually terminate TLS with that cert. Next's built-in server doesn't do TLS without a custom server (`server.js` + Node `https` module), which would be new backend code and complexity the request explicitly wants to avoid ("no changes to app code beyond what's needed").

The standard, much simpler mechanism is `tailscale serve https / http://localhost:3000` — Tailscale's own reverse proxy, which:
- terminates TLS using the tailnet cert automatically,
- **auto-renews the cert** (raw `tailscale cert` certs expire ~90 days and do NOT auto-renew unless served via `tailscale serve`/`funnel` — a manual `tailscale cert` invocation alone leaves you with a silent future outage unless someone crons a renewal),
- requires zero application code changes,
- binds only to the tailnet interface, so it can't accidentally leak to the public internet the way a raw `0.0.0.0:443` bind could.

Recommend the plan explicitly commit to `tailscale serve` rather than leaving "how to serve over HTTPS" to be decided during implementation — CLAUDE.md's "push back on unnecessary complexity" applies directly here, and getting this wrong (e.g., a from-scratch nginx/Node TLS setup) adds a new component and attack surface for no benefit.

## Security — the sharpest risk: `serve` vs `funnel`
`tailscale serve` (tailnet-only) and `tailscale funnel` (public internet) are one flag apart and easy to confuse. Given the entire point of this task is "nothing new exposed to the public internet," the plan/implementation should call out explicitly and verify **`funnel` must never be invoked**, and post-change validation should include `tailscale serve status` / `funnel status` output confirming funnel is off, not just a port scan.

Second gap: the request only requires confirming *no new* public exposure, not auditing *existing* exposure. Given the stated motivation is a CERT-Bund flag on a publicly-exposed service this same week, and memory indicates this VM currently "has no domain/SSL/CI/CD/backups/systemd" (i.e., likely still dev-box-postured), it's worth surfacing to the founder: does port 3000 (and/or 8000) currently listen on `0.0.0.0` and remain reachable from the public internet in plaintext? If so, this task as scoped leaves that plaintext path open, and the "private HTTPS access" goal is only additive, not a replacement, until that's explicitly decided. The request already anticipates this ambiguity ("confirm with founder before removing/breaking current access") — good — but I'd make it a required checkpoint rather than an implicit one, since silently leaving both paths open indefinitely undercuts the hardening intent.

## Eng Lead — dependencies requiring the founder, not just the agent
Two steps in this task cannot be completed by an autonomous agent and should be flagged as blocking dependencies up front rather than discovered mid-implementation:
1. **HTTPS Certificates must be enabled on the tailnet** in the Tailscale admin console (account-level setting, off by default) — `tailscale cert` fails without it.
2. **Joining the tailnet** (`tailscale up`) on a headless VPS needs either interactive browser auth (founder approves in their browser) or a pre-generated auth key from the admin console (founder must generate it). Neither can be done unattended.

## QA — validation plan is good but incomplete
The request's validation criteria (reachable via new HTTPS URL from a tailnet client; re-verify no new public exposure) are the right instincts. Add:
- Verify cert renewal actually works (or confirm `tailscale serve` is handling it), not just initial issuance — a cert that silently expires in 90 days is a regression nobody will notice until it breaks.
- If Supabase Auth is involved in any login flow tested from the new origin, confirm Supabase's allowed redirect URLs/site URL list includes the new `*.ts.net` origin — otherwise auth may break on that origin even though "no auth changes" were intended. This is config verification, not an auth *change*, but worth an explicit check since it's an easy silent failure.

## Governance
Framing is correct: infra change, founder-originated request constitutes the CEO approval CLAUDE.md requires, scope is bounded and explicit about what's deferred (public domain decision). One process note: confirm which AI-SDLC workflow type this should run under per `docs/operating-model/SDLC.md` — this reads as infrastructure/architecture-shaped (touches how the live instance is reached) rather than a standard feature workflow, and the two may have different review-lens or artifact requirements.

## Product / Investor Experience
Minimal relevance — single-user, founder-only instance, no user-facing surface changes. The only investor-trust angle is indirect: this correctly unblocks Secure-cookie auth work rather than retrofitting it later, which is the right sequencing call.

## Bottom line
Approve the intent as scoped, but before implementation starts, get explicit answers to: (1) commit to `tailscale serve` as the serving mechanism instead of leaving TLS termination undefined, (2) decide now whether existing plaintext port(s) stay open or get closed once the Tailscale URL works, and (3) flag the two founder-only setup steps (enable HTTPS certs in admin console, tailnet auth key) as prerequisites the agent can't self-serve.