# Architecture Decision Records (ADRs)

One short file per significant or hard-to-reverse technical decision. Scaffold with `/adr`.

**Format** (keep it under a page):

```
# NNNN — Title
- Status: Accepted | Superseded by NNNN | Proposed
- Date: YYYY-MM-DD
## Context        (what forced a decision)
## Decision       (what we chose)
## Consequences   (trade-offs, what this rules out)
```

Write an ADR when a choice affects architecture, data model, auth, security, infra, or build-vs-buy
— i.e. anything in the gated set (`../../operating-model/GOVERNANCE.md`). Numbering is sequential;
never rewrite history — supersede with a new ADR instead.

## Index
- [0001 — Monolith-first](0001-monolith-first.md)
- [0002 — Supabase Auth with ES256 JWT verification](0002-supabase-auth-es256.md)
- [0003 — RLS backstop via least-privileged app_user role](0003-rls-app_user-backstop.md)
- [0004 — In-process market cache + rate limiting](0004-market-cache-and-rate-limiting.md)
