#!/bin/bash
# Runs once, at first container init, before any Alembic migration. Creates the
# least-privilege app_user role that the existing RLS migration's grant block
# (6a8bdc1bb742) picks up automatically once it exists — same pattern the
# integration-test Postgres fixture uses (backend/tests/integration/conftest.py).
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE app_user LOGIN PASSWORD '$APP_USER_PASSWORD' NOINHERIT;
EOSQL
