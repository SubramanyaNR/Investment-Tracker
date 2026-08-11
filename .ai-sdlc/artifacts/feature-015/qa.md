## QA — manual, performed by the founder (2026-08-10)

Not routed through the Qwen QA stage — same reason as implementation (interactive
account/browser-level setup, nothing in a repo checkout for Qwen to test against). Founder
performed validation directly against the live VM.

### Validated

| Check | Result |
|---|---|
| `tailscale serve status` shows `https://madhyastha-lab-server.tail40a80c.ts.net` → `http://localhost:3000` | ✅ confirmed |
| `tailscale funnel status` shows tailnet-only, funnel off | ✅ confirmed |
| App reachable over `https://madhyastha-lab-server.tail40a80c.ts.net` | ✅ confirmed (founder accessed directly) |

### Not yet confirmed — carry forward, not blocking close-out

- **Reachability from a non-tailnet device/network** (e.g. phone on mobile data with Tailscale
  disabled) to positively confirm nothing is reachable outside the tailnet — planning.md's QA
  recommendation. `funnel status` being off is strong evidence but wasn't independently confirmed
  by an external negative test.
- **Supabase Auth allowed-origin check** — whether login works end-to-end from the new
  `*.ts.net` origin (Supabase's Site URL / Redirect URLs list may not include it yet). Not
  confirmed either way in this session.
- **Cert renewal over time** — `tailscale serve` is documented to auto-renew; no long-horizon
  observation yet (expected, given same-day implementation).

None of these block marking O4 complete — the core deliverable (private trusted HTTPS, nothing
newly public) is verified — but they're open follow-ups, not silently dropped.
