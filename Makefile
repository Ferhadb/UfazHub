# UFAZ Hub — developer shortcuts (wrap docker compose / uv / npm).
#
# Mode: dev compose by default. On the EC2 server run once:
#     echo 'PROD=1' > make.env
# (gitignored; auto-included below). Override any single invocation with:
#     make update PROD=1

-include make.env

PROD ?= 0
COMPOSE = docker compose -f docker-compose.yml
ifeq ($(PROD),1)
COMPOSE += -f docker-compose.prod.yml
endif

S ?= backend
TEST_DATABASE_URL ?= postgresql+asyncpg://postgres@localhost:5433/ufazhub_test

.DEFAULT_GOAL := help
.PHONY: help update deploy up down restart logs ps sh db install fe be \
        migrate docker-migrate revision test test-db lint format typegen \
        backup-now backups db-restore reset-db \
        playground playground-seed playground-reset playground-stop \
        playground-status playground-logs playground-db playground-accounts

help: ## Show this help
	@echo "UFAZ Hub make targets (compose mode: $(PROD))"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Compose lifecycle -------------------------------------------------------
update: ## Build images and (re)create containers [PROD=1 or make.env for prod]
	@echo "==> $(COMPOSE) build && up -d"
	@$(COMPOSE) build && $(COMPOSE) up -d

deploy: ## Server: git pull, back up the database, rebuild and restart
	@git pull --ff-only
	@$(MAKE) --no-print-directory backup-now
	@$(MAKE) --no-print-directory update

up: ## Start stack without rebuilding
	@$(COMPOSE) up -d

down: ## Stop stack (named data volumes are preserved)
	@$(COMPOSE) down

restart: ## Restart service(s) [S=backend|worker|frontend|db|redis|nginx]
	@$(COMPOSE) restart $(S)

logs: ## Follow logs [S=service, optional — defaults to all]
	@$(COMPOSE) logs -f --tail=100 $(S)

ps: ## Show container status
	@$(COMPOSE) ps

# --- Containers --------------------------------------------------------------
sh: ## Shell into a container [S=backend]
	@$(COMPOSE) exec $(S) sh

db: ## psql shell into the Postgres container
	@$(COMPOSE) exec db psql -U ufaz -d ufazhub

# --- Local dev loop ----------------------------------------------------------
fe: ## Frontend dev server (next dev)
	@cd frontend && npm run dev

be: ## Backend dev server (uvicorn --reload on :8000)
	@cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

install: ## Install/sync local deps (uv + npm ci)
	@cd backend && uv sync --dev
	@cd frontend && npm ci

typegen: ## Regenerate frontend API types from the FastAPI OpenAPI schema
	@cd backend && uv run python scripts/export_openapi.py > ../frontend/openapi.json
	@cd frontend && npm run typegen

# --- Local playground (local Postgres + fake data, no Docker) ----------------
playground: ## Start the local playground (seeds once, hot-reloads both apps)
	@bash scripts/playground.sh start

playground-seed: ## Rebuild the fake playground database (wipes local data)
	@bash scripts/playground.sh seed

playground-reset: ## Stop the playground, wipe the DB, and reseed
	@bash scripts/playground.sh reset

playground-stop: ## Stop playground dev servers
	@bash scripts/playground.sh stop

playground-status: ## Show playground process/DB status
	@bash scripts/playground.sh status

playground-logs: ## Tail playground backend + frontend logs
	@bash scripts/playground.sh logs

playground-db: ## psql shell for the playground database
	@bash scripts/playground.sh db

playground-accounts: ## Print seeded playground logins
	@bash scripts/playground.sh accounts

# --- Migrations --------------------------------------------------------------
migrate: ## Apply migrations (local uv; alembic inside container: docker-migrate)
	@cd backend && uv run alembic upgrade head

docker-migrate: ## Apply migrations inside the (running) backend container
	@$(COMPOSE) exec backend alembic upgrade head

revision: ## Autogenerate a migration [MSG="..." required]
	@if [ -z "$(MSG)" ]; then echo "usage: make revision MSG=\"add thing X\"" >&2; exit 1; fi
	@cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

# --- Checks (mirror CI) ------------------------------------------------------
test-db: ## Start the local test Postgres on :5433 (no Docker needed)
	@bash scripts/pg.sh start

test: test-db ## Backend test suite (real Postgres) + frontend unit tests
	@cd backend && TEST_DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest -q --cov=app.services --cov-fail-under=85
	@cd frontend && npm test

lint: test-db ## All CI checks: black, pytest, alembic check, prettier, eslint, tsc, typegen drift
	@cd backend && uv run black --check app tests scripts
	@cd backend && TEST_DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest -q --cov=app.services --cov-fail-under=85
	@cd frontend && npm run format:check && npm run lint && npm run typecheck && npm test
	@cd backend && uv run python scripts/export_openapi.py | diff -q - ../frontend/openapi.json >/dev/null || { echo "frontend/openapi.json is stale: run make typegen" >&2; exit 1; }

format: ## Apply formatters locally (black + prettier)
	@cd backend && uv run black app tests scripts
	@cd frontend && npm run format

# --- Backups -----------------------------------------------------------------
backup-now: ## Run one database backup immediately (dump into ./backups + Telegram copy)
	@$(COMPOSE) exec backup /usr/local/bin/db-backup.sh run

backups: ## List local backups inside the backup container
	@$(COMPOSE) exec backup ls -lh /backups

db-restore: ## Overwrite Postgres from a dump [FILE=backups/db_<stamp>.dump] (asks confirm)
	@if [ -z "$(FILE)" ]; then echo 'usage: make db-restore FILE=backups/db_2026-10-20_0317.dump' >&2; exit 1; fi
	@if [ ! -f "$(FILE)" ]; then echo "no such file: $(FILE)" >&2; exit 1; fi
	@bash -c "read -p 'This DROPS and restores the live database from $(FILE)? type yes: ' ok && [ \"$$ok\" = yes ] || { echo 'aborted'; exit 1; }"
	@$(COMPOSE) exec -T db psql -U ufaz -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='ufazhub' AND pid <> pg_backend_pid();"
	@$(COMPOSE) exec -T db dropdb -U ufaz --if-exists ufazhub
	@$(COMPOSE) exec -T db createdb -U ufaz ufazhub
	@$(COMPOSE) exec -T backup pg_restore -h db -Fc --no-owner -d "$$PGDATABASE" /backups/$(notdir $(FILE))
	@echo "==> restored. Restart the backend so it reconnects: make restart S=backend"

# --- Danger zone -------------------------------------------------------------
reset-db: ## DESTROY postgres + redis data volumes (asks for confirmation)
	@bash -c "read -p 'Delete all Postgres/Redis data for this project? type yes: ' ok && [ \"$$ok\" = yes ] || { echo 'aborted'; exit 1; }"
	@$(COMPOSE) down
	@docker volume rm -f $(notdir $(CURDIR))_postgres_data $(notdir $(CURDIR))_redis_data
	@echo "==> volumes removed; run 'make update' to recreate the stack"
