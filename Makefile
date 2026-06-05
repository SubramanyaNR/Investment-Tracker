SHELL := /bin/bash
BACKEND := backend
FRONTEND := frontend
API := http://127.0.0.1:8000
WEB := http://127.0.0.1:3000

.PHONY: help backend stop-backend build frontend stop-frontend dev restart stop logs validate migrate test test-int

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

backend: ## start backend on 127.0.0.1:8000 -> /tmp/it-backend.log
	@cd $(BACKEND) && nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 >/tmp/it-backend.log 2>&1 & echo $$! >/tmp/it-backend.pid
	@sleep 1 && echo "backend started (pid $$(cat /tmp/it-backend.pid))"

stop-backend: ## stop backend (frees :8000)
	@-fuser -k 8000/tcp >/dev/null 2>&1; rm -f /tmp/it-backend.pid; echo "backend stopped"

build: ## production build of frontend
	cd $(FRONTEND) && npm run build

frontend: build ## build + start frontend (prod) on :3000 -> /tmp/it-frontend.log
	@cd $(FRONTEND) && nohup npm start >/tmp/it-frontend.log 2>&1 & echo $$! >/tmp/it-frontend.pid
	@sleep 2 && echo "frontend started (pid $$(cat /tmp/it-frontend.pid))"

stop-frontend: ## stop frontend (frees :3000)
	@-fuser -k 3000/tcp >/dev/null 2>&1; rm -f /tmp/it-frontend.pid; echo "frontend stopped"

dev: backend frontend ## start full stack (backend + frontend prod; DB is Supabase, nothing local to start)

restart: stop backend frontend ## stop + rebuild + start everything

stop: stop-frontend stop-backend ## stop backend + frontend

logs: ## tail both logs
	tail -n 40 -f /tmp/it-backend.log /tmp/it-frontend.log

validate: ## quick health check of running stack
	@curl -s -m 5 $(API)/health >/dev/null && echo "backend: ok" || echo "backend: DOWN"
	@curl -s -m 8 -o /dev/null -w "frontend /api proxy: HTTP %{http_code}\n" $(WEB)/api/dashboard

migrate: ## alembic autogenerate+upgrade; usage: make migrate m="message"
	cd $(BACKEND) && source .venv/bin/activate && ./migrate.sh "$(m)"

test: ## run backend unit tests (fast, no Docker)
	cd $(BACKEND) && .venv/bin/python -m pytest -q -m "not integration"

test-int: ## run backend integration tests (testcontainers Postgres; needs Docker)
	cd $(BACKEND) && .venv/bin/python -m pytest -q -m integration

backup: ## pg_dump the Supabase DB to ./backups (timestamped, keeps last 7)
	@mkdir -p backups
	@url="$$(grep -E '^DATABASE_URL=' $(BACKEND)/.env | sed 's/^DATABASE_URL=//; s/+asyncpg//')"; \
	out="backups/it-$$(date +%Y%m%d-%H%M%S).sql"; \
	docker run --rm postgres:17 pg_dump "$$url?sslmode=require" > "$$out" \
	  && echo "wrote $$out ($$(du -h "$$out" | cut -f1))" \
	  || { echo "backup FAILED"; rm -f "$$out"; exit 1; }
	@ls -1t backups/*.sql 2>/dev/null | tail -n +8 | xargs -r rm -f
