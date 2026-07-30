# Review: Architecture-002 — Pivot to OSS Self-Hosted Single-User

## Overall assessment
The direction (drop hosted SaaS ambitions, go OSS/self-hosted/single-user) is coherent and actually *reduces* long-run complexity versus architecture-001's VPS-SaaS cutover — fewer moving parts, no billing, no multi-tenant isolation to get right under adversarial conditions. The phased-approval framing is correct given this simultaneously trips every CEO-gated category in CLAUDE.md. My concerns are about sequencing, some unresolved sub-decisions hiding inside "auth replacement," and a few things the request doesn't mention that should be forced into scope before implementation starts.

## Phasing — one sequencing objection
The proposed order is: schema/RLS decision → auth replacement → Docker Postgres packaging → data migration → docs. I'd flip the middle two. You can't meaningfully build or test "custom auth against vanilla Postgres" until vanilla Postgres actually exists as a target — building auth first against the current Supabase-hosted Postgres and swapping the DB underneath it later just means redoing integration testing twice. Recommend: (1) RLS decision, (2) stand up Docker Postgres + migration tooling as a dev target, (3) build+test auth against that target, (4) real data migration/cutover, (5) docs. This also gives you a disposable sandbox to break things in before touching the VM's real data.

## The auth replacement is under-specified for something flagged as "the single biggest, riskiest piece"
The request says "bcrypt + self-issued JWT" but leaves several decisions that are themselves security-model decisions and should be forced into the planning doc, not resolved implicitly during implementation:
- **Token revocation**: stateless self-issued JWTs can't be revoked. Need an explicit choice — short-lived access token + refresh token with a server-side revocation list, or accept unrevocable sessions until expiry. This is exactly the kind of thing the existing security backlog (RLS/rate-limiting/revocation, per prior audit) already flagged as missing — don't let the pivot quietly re-introduce the same gap under a new auth system.
- **Token storage**: httpOnly cookie (needs CSRF handling) vs localStorage/Authorization header (XSS exposure). Pick one and say why.
- **First-run bootstrap**: how does the single admin identity get created on a fresh `docker-compose up`? Env-var seeded credentials, or a first-load "claim this instance" wizard? This is a real UX/security decision, not an implementation detail — a self-hoster's very first experience with the security model.
- **Password reset**: Supabase Auth was presumably handling reset emails. A self-hosted single-user instance likely has no mail service. Either drop reset entirely (admin edits DB/env var to reset) or scope in SMTP config. Worth one sentence in the plan so it isn't discovered mid-implementation.
- **JWT algorithm/secret management**: HS256 with a generated secret in `.env` is the obvious self-hosted-appropriate choice (no JWKS needed since there's no external verifier) — state that explicitly since it's a real downgrade from the current ES256/JWKS setup, and confirm that's acceptable given the threat model change.

None of these need to be solved in this review, but the planning artifact should enumerate them as explicit decision points with recommendations, not fold them silently into "self-issued JWT."

## RLS decision
The request correctly frames this as a real choice rather than an obvious ripout. My read: rip it out. Keeping dormant RLS policies keyed on a hardcoded `app.current_user_id` is complexity with no present benefit and a latent footgun (a policy silently misconfigured or bypassed because nobody exercises the multi-user path). If cheap multi-user optionality matters later, that's better served by a clean re-add against a real requirement than by carrying dead policy code now. Flag the "possibly a demo instance" mention separately — a demo needs ephemeral/resettable data, not per-user RLS; don't let that requirement smuggle multi-tenancy back in through the side door.

## Data migration — the highest blast-radius item, thinnest treatment
This is the one part of the request that most needs strengthening before approval. The VM holds real portfolio data with no existing backup (a standing gap already on record). A Supabase→self-hosted-Postgres migration for production financial data needs, at minimum, stated in the plan:
- A backup taken and verified restorable *before* any schema/auth work touches the live DB.
- Whether Supabase Auth user records (UUIDs used as FKs throughout the schema) map 1:1 onto the new self-issued identity, or whether asset/transaction rows need a user_id remap.
- An explicit rollback point — if the new auth/DB stack breaks post-cutover, what's the path back to the working Supabase-backed instance.
This deserves to be its own phase with its own sign-off, not a bullet folded into "what this touches."

## Product/direction items not mentioned but implied
- **License choice** (MIT/Apache/AGPL etc.) is a real product-direction decision for an OSS release and isn't mentioned at all. Should be an explicit line item, likely bundled with the "docs/README for self-hosters" phase.
- **docs/product/VISION.md and ROADMAP.md** currently encode the ₹99/mo, 8-crore-TAM SaaS framing this pivot cancels. The request says architecture-001 is superseded via its `status.yaml`, but VISION/ROADMAP themselves will keep asserting the old direction until edited. Since product-direction changes are CEO-gated, the plan should propose the specific rewritten VISION/ROADMAP language for sign-off rather than leaving stale docs as the source of truth alongside a new architecture doc.

## Testing/validation gap
The request already flags "no automated test suite gates this" as a constraint rather than a risk to close. For a from-scratch auth system handling real financial data, I'd push back on treating this as acceptable-as-is: at minimum, the auth replacement phase should ship with its own test coverage (login, token expiry, bootstrap, ownership checks) before it's considered done — consistent with this project's own Validation Requirements ("never declare success from code inspection alone"). The e2e-ui-test skill update mentioned should be scoped as a deliverable of the auth phase, not an afterthought.

## Summary of recommended changes to the plan before CEO sign-off
1. Reorder phases: infra (Docker Postgres + migration tooling) before auth build-out.
2. Expand the auth phase to explicitly decide: revocation strategy, token storage, first-run bootstrap, password reset, JWT algorithm/secret handling.
3. Elevate data migration to its own gated phase with mandatory pre-migration backup + verified restore + rollback point.
4. Add license choice and VISION/ROADMAP rewrite as explicit, CEO-approved deliverables, not implied side effects.
5. Require auth-phase test coverage as a completion condition, not a deferred nice-to-have.

Nothing here blocks the overall direction — it's sound and simplifies the system. The gaps are all in making sure each CEO-gated sub-decision is surfaced and approved individually rather than approved once as a bundle and then decided ad hoc during implementation.

## CEO decisions (recorded 2026-07-30)

- **Phase order**: adopted as recommended — Docker Postgres + migration tooling stood up before auth build-out.
- **RLS**: rip out entirely (adopted as recommended).
- **JWT algorithm**: HS256 with a generated secret in `.env` (adopted as recommended).
- **Token storage**: **httpOnly cookie**, with CSRF handling (SameSite + CSRF token on state-changing requests).
- **Revocation strategy**: **short-lived access token + server-tracked refresh token**, revocable on logout/password change.
- **First-run bootstrap**: **env-var seeded credentials** (`ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env`, read on first boot). No setup wizard.
- **Password reset**: follows from the above — no email/SMTP flow; admin resets by editing `.env` (or DB directly) and restarting. No in-app reset flow planned.
- **License**: **MIT**.
- **Data migration**: elevated to its own gated phase, per the review — mandatory backup + verified restore + explicit rollback point before touching the live DB.
- **Auth-phase test coverage**: required as a completion condition (login, token expiry/refresh, revocation, bootstrap, ownership checks) — not deferred.
- **VISION.md / ROADMAP.md rewrite**: to be drafted as an explicit deliverable for CEO review (not silently edited), reflecting the OSS/self-hosted/single-user direction.

All open sub-decisions from the planning review are now resolved. Proceeding to implementation is
contingent on final explicit CEO approval of this consolidated plan.

## SCOPE FOR THIS IMPLEMENTATION PASS — read before writing any code

CEO approval is for the full phased plan, but **this specific implementation run is scoped to
Phase 1 only**: stand up self-hosted Postgres in Docker (e.g. a `docker-compose.yml` service) plus
whatever migration tooling is needed to create the schema there, as an **isolated sandbox** —
NOT touching the live VM's real database, real `.env` files, or any real user data.

Do NOT in this pass:
- Write or wire up any auth code (bcrypt/JWT/cookies/refresh tokens) — that's Phase 2, against
  this new Postgres target, once Phase 1 is reviewed and confirmed working.
- Touch, migrate, or export the live Supabase data — that's Phase 3, gated separately.
- Remove Supabase from the running app, RLS policies, or existing auth code — the current
  Supabase-backed app must keep working untouched until later phases are explicitly approved.
- Edit `VISION.md`/`ROADMAP.md` — that's a docs deliverable for a later phase.

Deliverable for this pass: a working, isolated Postgres-in-Docker instance the next phase can
build and test auth against, plus a short note on how migrations will be created/applied against
it (e.g. reusing the existing Alembic setup pointed at the new target).