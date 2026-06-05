# 0004 — In-process market cache + rate limiting

- Status: Accepted
- Date: 2026-06-05

## Context
Audit finding M2: public `/market/*` is uncached (anonymous traffic burns CoinGecko/MFAPI
free-tier limits = cost/abuse amplification) and there is no rate limiting. A blocker before
exposing the app on a public VPS. Constraints: solo founder, 0–1000 users, monolith, single
uvicorn worker, no premature infrastructure.

## Decision
- **Caching** at the integration layer (`get_top_cryptos`, `get_crypto_prices`, `get_latest_nav`,
  `search_schemes`) via a small in-process async TTL cache (`core/cache.py`) with per-key
  single-flight and serve-stale-on-error. TTLs: crypto 60s, NAV 5min, scheme search 1h. This also
  benefits the authenticated recalc/scheduler paths (shared functions).
- **Rate limiting** as FastAPI dependencies (`core/ratelimit.py`, fixed-window): **per-user** (JWT
  `sub`) on every authenticated router (general 120/min; recalculate 10/min; insights 6/min), and
  **per-IP** on public `/market/*` (60/min; search 30/min). 429 + `Retry-After` on breach.
- **No Redis, no new dependencies.** In-process state is consistent on one worker and Redis-swappable
  later. Structured `event=cache.hit|miss|stale` / `ratelimit.block` logging for production validation.

## Consequences
- Upstream cost amplification is closed regardless of inbound volume (a 60s TTL = ~1 upstream
  call/min/key for any user count). Per-user limits are reliable now.
- **Per-IP is degenerate on the VM today:** Next.js `rewrites()` does not forward `X-Forwarded-For`,
  so the backend sees `peer=127.0.0.1` for all proxied traffic — per-IP `/market` is currently one
  shared global bucket (a coarse backstop), and becomes per-client once **nginx (B1)** forwards the
  real client IP (`trust_forwarded_for` already honours it).
- **Not closed:** the JWKS unknown-`kid` amplification half of M2 (a bad-`kid` negative cache or edge
  per-IP) — deferred.
- Multiple workers/instances would make the in-memory cache/limits per-worker → switch to Redis then.
