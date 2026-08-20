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

Login is **disabled by default** (`AUTH_ENABLED=false`) — fine for a single local device, and
you'll see a warning banner reminding you of that. If this instance is reachable by more than
just you (a VPS, a cloud box, Tailscale), run `make reset-admin-password` to set real credentials
(the `ADMIN_PASSWORD` in `.env` is only a placeholder), then set `AUTH_ENABLED=true` and restart.

To stop it: `docker compose down` (add `-v` to also wipe the database volume).

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
