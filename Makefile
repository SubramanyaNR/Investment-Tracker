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

dev: backend frontend ## start full stack (backend + frontend prod; DB is a long-running local Postgres container, nothing to start here)

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

DB_CONTAINER := investment_tracker_postgres
DB_NAME := investment_tracker
DB_USER := investment_admin

backup: ## pg_dump the local Postgres container to ./backups (timestamped, gzipped, keeps last 30)
	@mkdir -p backups && chmod 700 backups
	@find backups -name '*.sql.gz.tmp.*' -mtime +1 -delete 2>/dev/null || true
	@set -o pipefail; \
	final="backups/it-$$(date +%Y%m%d-%H%M%S).sql.gz"; \
	tmp="$$final.tmp.$$$$"; \
	docker exec $(DB_CONTAINER) pg_dump -U $(DB_USER) $(DB_NAME) | gzip > "$$tmp" \
	  || { echo "backup FAILED (pg_dump/gzip)"; rm -f "$$tmp"; exit 1; }; \
	gzip -t "$$tmp" || { echo "backup FAILED (corrupt gzip)"; rm -f "$$tmp"; exit 1; }; \
	bytes=$$(stat -c%s "$$tmp" 2>/dev/null || stat -f%z "$$tmp"); \
	if [ "$$bytes" -lt 500 ]; then echo "backup FAILED (suspiciously small: $${bytes} bytes)"; rm -f "$$tmp"; exit 1; fi; \
	chmod 600 "$$tmp"; \
	mv "$$tmp" "$$final"; \
	echo "wrote $$final ($$(du -h "$$final" | cut -f1))"
	@ls -1t backups/*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm -f
