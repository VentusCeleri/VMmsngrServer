#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="docker-compose.prod.yml"

cd "${ROOT_DIR}"

if [[ ! -f ".env" ]]; then
  echo "Missing .env. Create it on the VPS from .env.example and fill production values." >&2
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Working tree is not clean. Commit/stash local changes before deployment." >&2
  exit 1
fi

echo "Pulling latest code..."
git pull --ff-only

echo "Building production image..."
docker compose -f "${COMPOSE_FILE}" build

echo "Applying migrations..."
docker compose -f "${COMPOSE_FILE}" run --rm api alembic upgrade head

echo "Starting services..."
docker compose -f "${COMPOSE_FILE}" up -d

echo "Waiting for readiness..."
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8000/ready >/dev/null; then
    echo "API is ready."
    docker compose -f "${COMPOSE_FILE}" ps
    exit 0
  fi
  sleep 2
done

echo "API did not become ready in time. Recent logs:" >&2
docker compose -f "${COMPOSE_FILE}" logs --tail=100 api >&2
exit 1
