# Memory Index

- [Multi-agent orchestration: merged & live](ai-sdlc-orchestration-branch-unmerged.md) — Gemini implements, Qwen tests (via OpenRouter), Claude orchestrates; see SDLC.md for full workflow
- [AI-SDLC model adapters verified](ai-sdlc-model-adapters-verified.md) — Qwen/Claude work; Gemini was faking implementations until --approval-mode auto_edit fix (gemini.py)
- [POST /assets merges MF/crypto by scheme/coin](post-assets-merges-by-scheme-or-coin.md) — creating a "temp" MF/crypto with an existing scheme_code/coingecko_id mutates the real asset
- [No DB backups exist](no-db-backups-exist.md) — destructive DB mistakes are irreversible; capture state first
- [Frontend accessed by VM IP via /api proxy](frontend-accessed-by-vm-ip-via-api-proxy.md) — browser opens 172.23.80.6:3000; uses same-origin /api proxy, never localhost:8000
- [VPS todo: automated offsite backups](vps-deploy-todo-automated-offsite-backups.md) — cron `make backup` + rclone offsite + test restore, on the VPS (Supabase free has no auto-backups)
- [Security audit + hardening backlog](security-audit-and-hardening-backlog.md) — auth/multi-tenancy audit in docs/runbooks/SECURITY-AUDIT.md; RLS/least-priv role, rate limiting, revocation still required before paying users
- [Google OAuth deferred until VPS](google-oauth-deferred-until-vps.md) — email/password works now; Google login left disabled until real domain (provider not enabled in Supabase)
- [Operating model: SDLC + CEO gate](operating-model-sdlc-gate.md) — run /feature for any non-trivial change; 7 review lenses + approval gate enforced by .claude/hooks/gate.sh; keyed docs via docs/INDEX.md
- [Gate-hook substring false-positive](gate-hook-substring-false-positive.md) — low-pri: gate.sh substring-matches "alembic upgrade"/"make migrate" incl. commit messages; deferred fix
- [Backlog: intraday prices for 1D chart](backlog-intraday-prices.md) — 1D range on Net Worth chart is meaningless until intraday prices stored; crypto-only via CoinGecko hourly; MF NAV is once-daily by AMFI definition
- [Backlog: historical net worth from transactions](backlog-historical-networth-from-transactions.md) — reconstruct portfolio_snapshots from transaction history + historical prices (CoinGecko max, MFAPI, FI formula); full investment journey view
- [e2e test corrupted real BTC holding](e2e-test-corrupted-real-btc-holding.md) — 2026-07-30: harness assumed "bitcoin" was unheld, merged test buys into real BTC via POST /assets; fixed + harness now checks live, never hardcode "safe" identifiers
- [MFAPI unreachable from this VM](mfapi-unreachable-from-this-vm.md) — api.mfapi.in TCP connect hangs (egress/firewall issue post-migration), while CoinGecko + general internet work; check this before assuming a code regression on MF search failures
