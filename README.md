# WealthSignal

A self-hosted, multi-asset portfolio tracker for Indian retail investors — Crypto, Mutual Funds,
FD, RD, PPF, and Savings Accounts, all in one place.

WealthSignal is **not** a trading platform, brokerage, budgeting app, or expense tracker. It's
built for one thing: portfolio observability. Understand your net worth, P&L, asset allocation,
and performance across every platform you invest through, from a single interface you run
yourself.

Free, MIT-licensed, single-user by design — your data stays on your own machine or server, never
sent to a third-party SaaS.

## Features

- Track Crypto (live prices via CoinGecko), Mutual Funds (live NAV via MFAPI, auto-SIP, partial
  redeem), FD/RD/PPF/Savings (compound interest, top-ups), and manually-tracked assets (real
  estate, gold, unlisted shares)
- Dashboard: net worth, P&L, allocation and liquidity breakdowns, net worth over time
- XIRR — portfolio-level and per-asset annualised returns
- Performance movers — best/worst performing assets, daily and monthly
- Transaction history with CSV import for backfilling past data
- AI-generated portfolio insights (optional — rule-based by default, or bring your own Gemini API
  key)
- Dark/light theme

## Tech stack

FastAPI (async SQLAlchemy + asyncpg) · Next.js 16 / React 19 · PostgreSQL 16 · Tailwind 4

## Quick start (Docker Compose)

Requires Docker and Docker Compose.

```bash
git clone https://github.com/SubramanyaNR/Investment-Tracker.git
cd Investment-Tracker
cp .env.example .env
```

Edit `.env` — at minimum set `POSTGRES_PASSWORD`, `JWT_SECRET` (generate one with
`openssl rand -hex 32`), `ADMIN_EMAIL`, and `ADMIN_PASSWORD`. `ADMIN_EMAIL`/`ADMIN_PASSWORD`
create your one admin account on first run only.

```bash
docker compose up -d --build
```

The app is now running at `http://localhost:3000`.

To stop it: `docker compose down` (add `-v` to also wipe the database volume).

## Authentication

Login is **disabled by default** (`AUTH_ENABLED=false`) — every request acts as the single admin
user, no password needed. Fine for a single local device; a warning banner is shown in the app
the whole time this is off, since anyone who can reach the address has full access.

If this instance is reachable by more than just you (a VPS, a cloud box, Tailscale, etc.), enable
login:

1. **Set a real password first** — the `ADMIN_PASSWORD` in `.env` is only a placeholder. Run:
   ```bash
   make reset-admin-password
   ```
   It prompts interactively for a new email (optional, keeps the current one if left blank) and a
   new password (hidden input, confirmed twice). This is also how you change credentials later —
   editing `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env` after first boot has no effect.

2. **Turn login on** — set in `.env`:
   ```
   AUTH_ENABLED=true
   ```

3. **Restart** the backend (`docker compose restart backend`, or `make backend` if running via
   systemd) and log in with the credentials you just set.

To go back to no-login mode, set `AUTH_ENABLED=false` and restart again — none of your data is
affected either way, since there's only ever the one admin account regardless of the setting.

## Running without Docker

See `docs/runbooks/LOCAL-DEV.md` for running the backend (`uvicorn`) and frontend (`next build` +
`next start`) directly against your own Postgres instance.

## Exposing this beyond localhost

The app ships listening on plain HTTP with `COOKIE_SECURE=false` so it works out of the box with
zero setup. If you expose it beyond `localhost`/your LAN — over the public internet, or even a
private tailnet — put real HTTPS in front of it (e.g. [Tailscale](https://tailscale.com/) `serve`,
or your own reverse proxy + TLS cert) and set `COOKIE_SECURE=true`, or your session cookie travels
in plaintext. See `docs/runbooks/DEPLOY.md`.

## Documentation

Start at `docs/INDEX.md` for architecture, runbooks, and product docs.

## License

MIT — see `LICENSE`.
