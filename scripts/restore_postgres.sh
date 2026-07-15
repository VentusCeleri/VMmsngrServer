#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_PATH="${1:-}"

cd "${ROOT_DIR}"

if [[ -z "${BACKUP_PATH}" ]]; then
  echo "Usage: scripts/restore_postgres.sh /path/to/backup.sql.gz" >&2
  exit 1
fi

if [[ ! -f "${BACKUP_PATH}" ]]; then
  echo "Backup file does not exist: ${BACKUP_PATH}" >&2
  exit 1
fi

if [[ ! -f ".env" ]]; then
  echo "Missing .env. Create it from .env.example before running restore." >&2
  exit 1
fi

echo "WARNING: restore will overwrite data in the configured PostgreSQL database."
echo "Backup: ${BACKUP_PATH}"
read -r -p "Type RESTORE to continue: " confirmation
if [[ "${confirmation}" != "RESTORE" ]]; then
  echo "Restore cancelled."
  exit 1
fi

gunzip -c "${BACKUP_PATH}" \
  | docker compose -f "${COMPOSE_FILE}" exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

echo "Restore completed from: ${BACKUP_PATH}"
