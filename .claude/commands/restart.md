---
description: Rebuild frontend and restart backend + frontend
---

Run `make restart` (stops services, rebuilds the frontend, starts postgres + backend + frontend prod), then `make validate`. Report the pids and health. If validate fails, check `/tmp/it-backend.log` and `/tmp/it-frontend.log`.
