#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: ./migrate.sh \"describe what you changed\""
  echo "Example: ./migrate.sh \"add broker_name to assets\""
  exit 1
fi

echo "Generating migration: $1"
python3.11 -m alembic revision --autogenerate -m "$1"

echo "Applying migration..."
python3.11 -m alembic upgrade head

echo "Done. Current state:"
python3.11 -m alembic current
