# 0001 — Monolith-first architecture

- Status: Accepted
- Date: 2026-06-04 (recorded; decision predates this ADR)

## Context
Solo founder, pre-production, 0 users, targeting 0–100 first and ≤500 without re-architecture.
Limited budget; the economics are ₹99/month on a ~$5/month Hetzner CX21.

## Decision
A single FastAPI backend + Next.js frontend + one Postgres, deployed via Docker Compose. No
microservices, no Kubernetes, no event-driven/CQRS/event-sourcing. Backend internal structure is
layered (`api/` → `services/` → `integrations/` → `db/`) but ships as one process.

## Consequences
- Fastest path to ship and easiest to operate solo; one log, one deploy, one DB.
- Comfortably serves 100–10,000 users on one CX21 with 60s response caching.
- Rules out independent service scaling — acceptable until 10,000+ users.
- Revisiting any of these requires sign-off from both CTO and Architect lenses with written
  justification (`../../operating-model/GOVERNANCE.md`).
