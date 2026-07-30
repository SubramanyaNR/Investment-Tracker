---
name: mfapi-unreachable-from-this-vm
description: "api.mfapi.in (MF NAV/search provider) is unreachable from this VM's network — TCP connect to :443 hangs — while general internet and CoinGecko work fine. Infra/firewall issue, not app code."
metadata: 
  node_type: memory
  type: project
  originSessionId: 4ad21862-5ab8-4926-88c0-88f8decd0117
  modified: 2026-07-30T10:21:09.145Z
---

Discovered 2026-07-30 while running the `e2e-ui-test` skill after a VM migration: `GET
/market/mutual-funds/search` returns 502 after ~10s. `MFAPI_BASE_URL=https://api.mfapi.in/mf` is
configured correctly and DNS resolves (`142.93.217.120`), but a raw `curl`/TCP connect to
`api.mfapi.in:443` hangs and times out, while `https://www.google.com` and CoinGecko
(`/market/crypto/top`) both respond instantly. This is a network egress block specific to that host
on this VM (likely a firewall/allowlist gap from the migration), not an application bug.

**How to apply:** if MF search/add fails with a 502 and the backend log shows a ~10s delay before it,
check this first — `curl -m 8 https://api.mfapi.in/mf/search?q=parag` — before assuming a code
regression. Fixing it is an infra task (VM firewall/egress rules), outside normal engineering scope;
flag to the founder rather than trying to work around it in application code. Related:
[[e2e-test-corrupted-real-btc-holding]] (this blocker forced skipping the MF step during that
incident's diagnosis).
