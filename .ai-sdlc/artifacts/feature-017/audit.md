## Audit — Custom Auth Cutover (Planning → Implementation → QA)

### Overall verdict
The execution broadly delivered against the approved plan, and the QA pass is unusually rigorous (211 automated tests + 15 live adversarial checks against the real running instance, not just the suite). Two real bugs were caught before reaching production. That said, there's one process issue that should be surfaced explicitly to the founder, and a few of the Planning doc's own open items are closed by documentation rather than by the underlying risk actually going away.

### Governance — the issue that matters most here
**Claude implemented and then QA'd its own security-critical auth rewrite.** The multi-agent SDLC model exists specifically so implementation (Gemini) and testing (Qwen) are independent of the orchestrator (Claude) — this is a real control, not a formality, especially for an auth rewrite that is a gated category. Both fallbacks happened for infra reasons (Gemini quota, Qwen/OpenRouter key invalid) rather than any decision to bypass the control, and the founder did direct the fallback per the doc — but the net effect is that no independent party verified this code. That's worth a one-line explicit acknowledgment in the artifact ("founder accepted same-agent impl+QA for this cutover due to tooling outage") rather than being implied only by two separate incident notes. Recommend re-running an independent review (even a fresh Claude session with no memory of writing the code, or a manual founder read of `auth.py`/`main.py` CSRF middleware) before this is trusted as fully closed, given it's the sole authentication boundary for the whole app now.

### Security
- **`COOKIE_SECURE=false` on a publicly-routable IP is the standout residual risk**, and it's handled the right way procedurally (documented as open, explicitly not silently fixed, framed as no-worse-than-the-prior-Bearer-token path) — but the framing undersells one thing: previously, token theft required intercepting an `Authorization` header on individual API calls; now a stolen cookie is a full, replayable session (and CSRF token is also transmitted in the clear). The blast radius per successful interception went up even if the exposure mechanism (plaintext HTTP) is unchanged. Worth a sentence to that effect so the founder is deciding with full information, not just "same as before."
- **Refresh-token reuse detection**: QA confirms reuse of a rotated-out token returns 401, but doesn't state whether reuse revokes the *entire* token family/session (the standard behavior for theft detection) or just rejects that one token while a concurrently-issued valid refresh token continues to work. If it's the latter, an attacker who stole a refresh token mid-rotation-race gets silently locked out but the legitimate session is undisturbed — which is fine for UX but means theft is not actually detected/alarmed anywhere. Worth a one-line clarification.
- **RLS removal is a full defense-in-depth downgrade**, correctly justified by the single-user model, but note it also deleted the RLS backstop test suite (`test_rls_backstop.py`). If multi-user ever returns to the roadmap, there's now zero regression coverage forcing RLS to be reintroduced correctly — pure app-layer filtering is the only thing standing between tenants at that point. Not a blocker now; flag it in the tech-debt register so it isn't forgotten.
- Rate limiting, CSRF double-submit enforcement, bootstrap idempotency, and old-JWT rejection were all concretely verified live rather than asserted — this is genuinely good practice and should be the bar going forward.

### Architecture
- Compose project-name collision (sandbox container nearly clobbered) is a good catch, but it's also a signal: two docker-compose files coexisting in the same directory without namespacing is a fragile setup pattern in general, not just for this incident. Worth a follow-up note in tech debt rather than trusting `-p` discipline to hold indefinitely.
- Supabase SDK removal from frontend is confirmed done; worth double-checking `frontend/package-lock.json` no longer resolves any transitive `@supabase/*` entries, since a stale lockfile reference wouldn't break the build but would be a leftover attack-surface/audit item.

### QA
- The one gap flagged as "not independently verified" — real browser session, cookie persistence across page loads, the 10-minute proactive refresh timer actually firing — is the part most likely to surface as a real bug (curl doesn't exercise the browser's cookie jar, tab lifecycle, or timer drift the way a live session does). Given this is the sole login path with no fallback, recommend closing this specific gap before calling the feature done, not just carrying it forward as a footnote.
- Good discipline flagging the doc sweep (SECURITY-AUDIT.md, DEPLOY.md, BACKUP-RESTORE.md) as explicitly out of scope rather than silently expanding — but these docs describing a security model (Supabase/RLS) that no longer exists is itself a small trust risk if anyone reads them as current. Recommend a tracked follow-up ticket, not just a mention in this artifact.

### Product / Investor Experience
No end-user-facing risk given single-user scope — appropriately treated as low priority throughout.

### Summary of what to close before calling this fully done
1. Explicit founder sign-off statement on same-agent impl+QA (governance transparency, not a redo).
2. Clarify whether refresh-token reuse revokes the session/family or just the one token.
3. One real browser end-to-end login + idle-tab refresh-timer test.
4. Add RLS-removal and stale doc references to the tech-debt register (both already identified, neither yet formally tracked).