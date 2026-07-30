# Review: Production VPS Cutover (Architecture Request)

## Governance check
Confirmed: this correctly triggers the CEO approval gate under `docs/CLAUDE.md` — infra, production deployment, and auth *configuration* (Site URL/Redirect/CORS) are all listed gated categories, even though the auth *model* (Supabase JWT) is untouched. The request's own recommendation to phase this into separable approvals is sound and I'd approve that framing, but I'd adjust the proposed order (see below).

## Sequencing — recommended reorder
Proposed order: domain/SSL → Supabase cutover → CI/CD → backups/monitoring.

I'd resequence based on dependency and risk, not just logical grouping:

1. **Backups first (or in parallel), not last.** This has zero dependency on domain/SSL/CI-CD and is the single highest-risk gap — no backup has ever been taken, Supabase free tier has no automatic PITR (per prior memory), and this is real portfolio data. Pushing it to the end of a 4-phase rollout means the longest possible window of a single-copy production database. Pull it forward.
2. **Process supervision (systemd) second.** Also independent of domain/auth. The current bare-`nohup` setup is the most acute reliability gap (doesn't survive reboot) and de-risks everything that follows — you don't want to be debugging Nginx/Certbot on a process that a stray reboot silently kills.
3. **Domain + HTTPS third** — genuinely a prerequisite for step 4.
4. **Supabase auth cutover fourth** — correctly depends on the domain/HTTPS existing (Site URL/Redirect URLs need the real HTTPS domain).
5. **CI/CD last, and scoped conservatively.** Auto-deploy-on-push-to-master is the highest blast-radius item here because there's explicitly no automated test suite gating it yet. Recommend it *not* auto-deploy on every push initially — gate it behind a manual workflow_dispatch trigger or required approval step until test coverage exists, otherwise this phase converts "no tests" into "no tests, deployed automatically."
6. **Uptime monitoring** is read-only external polling against a public endpoint — arguably doesn't need to sit behind the same gate as the others (no state change on the VM), can be done anytime, including in parallel with anything else.

## Security lens
- **CORS_ORIGINS / Supabase Site URL cutover**: make sure `localhost:3000` is *removed*, not left alongside the new domain — a stale dev origin left trusted in production is exactly the kind of thing that gets missed and lingers.
- **Egress/firewall**: the `api.mfapi.in` unreachability (separate memory entry) smells like a security-group/outbound-rule gap on this fresh VM. Since Domain+HTTPS work will already involve reviewing inbound rules (80/443/SSH), fold a matching *outbound* egress audit into that same phase rather than treating it as a coincidence to investigate later — likely same root cause.
- **CI/CD secrets**: whatever SSH key/token GitHub Actions uses for deploy should be a scoped, deploy-only credential, not a reused personal key.
- **Backup encryption**: pg_dump output headed to a personal Google Drive via rclone should be encrypted at rest (e.g., gpg) before upload — it's financial PII leaving your infra boundary onto a third-party consumer service.

## Architecture lens
- `docker-compose.yml` exists but isn't what's running. This request implicitly needs a decision — systemd units *or* docker-compose, not both — and that choice should be made explicitly and recorded (ADR-worthy), not left implicit in whichever gets implemented first. For a $5/mo single-user box, bare systemd units are the lower-overhead choice (no Docker daemon tax); docker-compose buys environment parity you don't yet need. Lean systemd unless there's a reason I'm missing.

## QA / Validation lens
Given no automated test suite gates infra, each phase needs an explicit manual validation step before moving to the next — not just "make validate" at the very end:
- Nginx/Certbot: `certbot renew --dry-run` must pass, not just initial cert issuance.
- systemd: validate with an actual `reboot`, not `systemctl restart` — the whole point is surviving a reboot.
- Supabase cutover: verify login/OAuth against the real domain *and* verify the old localhost redirect URL no longer works (negative test, not just positive).
- Backups: a real **restore drill** into a scratch DB, not just a successful `pg_dump` — "backup exists" and "backup restores" are different claims and the request correctly calls this out; don't let it get skipped under time pressure.
- CI/CD: prove a bad commit can be rolled back before trusting it for real changes.

## Product / Investor Experience lens
No user-facing change; pure infra maturity aligned with roadmap V2–V7. Net positive for investor trust once live (HTTPS padlock, working Google OAuth, uptime visibility). Brief outages during cutover (DNS switch, process migration) are acceptable given no paying users/SLA yet, but each phase should still be done as a discrete, validated window rather than improvised live.

## Bottom line
Phased approval is the right call. I'd re-order to: **backups → process supervision → domain/SSL → Supabase cutover → CI/CD (manual-trigger initially) → monitoring**, fold an outbound egress audit into the domain/SSL phase, and require a real restore drill and real reboot test as acceptance criteria for their respective phases — not just "the command exited 0." This still stops at the CEO gate per governance; happy to proceed phase-by-phase once you approve the sequencing.