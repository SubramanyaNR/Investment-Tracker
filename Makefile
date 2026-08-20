SHELL := /bin/bash
BACKEND := backend
FRONTEND := frontend
API := http://127.0.0.1:8000
WEB := http://127.0.0.1:3000

.PHONY: help backend stop-backend build frontend stop-frontend dev restart stop logs validate migrate test test-int install-services reset-admin-password

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

install-services: ## one-time: install/enable systemd units for backend + frontend (run after editing deploy/systemd/*.service)
	cp deploy/systemd/it-backend.service deploy/systemd/it-frontend.service /etc/systemd/system/
	systemctl daemon-reload
	systemctl enable it-backend it-frontend
	@echo "installed. use 'make backend'/'make frontend'/'make dev' to start."

backend: ## (re)start backend via systemd, picks up code changes on restart
	systemctl restart it-backend
	@sleep 1 && systemctl --no-pager --lines=0 status it-backend

stop-backend: ## stop backend
	systemctl stop it-backend

build: ## production build of frontend
	cd $(FRONTEND) && npm run build

frontend: build ## build + (re)start frontend via systemd, picks up new build on restart
	systemctl restart it-frontend
	@sleep 2 && systemctl --no-pager --lines=0 status it-frontend

stop-frontend: ## stop frontend
	systemctl stop it-frontend

dev: backend frontend ## (re)start full stack (backend + frontend); DB is a long-running local Postgres container, nothing to start here

restart: dev ## alias for dev — stop/rebuild/start everything via systemd

stop: stop-frontend stop-backend ## stop backend + frontend

logs: ## tail both logs (systemd journal)
	journalctl -u it-backend -u it-frontend -f -n 40

validate: ## quick health check of running stack
	@curl -s -m 5 $(API)/health >/dev/null && echo "backend: ok" || echo "backend: DOWN"
	@curl -s -m 8 -o /dev/null -w "frontend /api proxy: HTTP %{http_code}\n" $(WEB)/api/dashboard

migrate: ## alembic autogenerate+upgrade; usage: make migrate m="message"
	cd $(BACKEND) && source .venv/bin/activate && ./migrate.sh "$(m)"

reset-admin-password: ## interactively reset the admin email/password + revoke active sessions
	cd $(BACKEND) && source .venv/bin/activate && python3.11 -m scripts.reset_admin_password

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
