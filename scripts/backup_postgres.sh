#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backups}"

cd "${ROOT_DIR}"

if [[ ! -f ".env" ]]; then
  echo "Missing .env. Create it from .env.example before running backup." >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

timestamp="$(date -u +"%Y%m%dT%H%M%SZ")"
backup_path="${BACKUP_DIR}/vmmsngr-postgres-${timestamp}.sql.gz"

docker compose -f "${COMPOSE_FILE}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  | gzip > "${backup_path}"

chmod 600 "${backup_path}"
echo "Backup created: ${backup_path}"
