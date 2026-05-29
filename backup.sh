#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${ROOT}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="investment_db_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Creating backup: $FILENAME"
docker compose -f "${ROOT}/docker-compose.yml" exec -T postgres \
  pg_dump -U investment_user investment_db | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "Saved: ${BACKUP_DIR}/${FILENAME}"

# Keep only last 7 backups
ls -t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm --

echo "Current backups:"
ls -lh "${BACKUP_DIR}/"
