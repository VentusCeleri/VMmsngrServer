# VMmsngrServer

Own Server backend for VMmsngr, a private family messenger and organizer for two people.

## Stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- JWT auth
- WebSocket realtime
- APNs push notification provider
- Basic presence
- MVP rate limiting
- Docker Compose for local development and production VPS

No AI, Redis, E2E encryption, file storage, Kubernetes or automatic GitHub deployment are included in v1.5.

## Project Structure

```text
VMmsngrServer/
  app/                  FastAPI app, routes, config, models, services
  alembic/              database migrations
  deploy/nginx/         Nginx reverse proxy examples
  docs/                 production, deployment and backup docs
  scripts/              safe deploy/backup/restore helpers
  tests/                backend contract and infrastructure tests
  docker-compose.yml    local development
  docker-compose.prod.yml production VPS
  Dockerfile
  requirements.txt
```

## Local Development

```bash
cd /Users/mapku3/Documents/VMmsngrServer
cp .env.example .env
docker compose up --build
```

The local API is available at:

- API: <http://localhost:8000>
- Health: <http://localhost:8000/health>
- Readiness: <http://localhost:8000/ready>
- OpenAPI docs: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

Local compose intentionally keeps developer conveniences:

- source mounted into `/app`;
- Uvicorn `--reload`;
- PostgreSQL exposed on `5432`;
- API exposed on `8000`.

## Production VPS

Production uses `docker-compose.prod.yml`.

Key differences:

- PostgreSQL has no public port;
- API binds only to `127.0.0.1:8000`;
- no source-code bind mount;
- no Uvicorn `--reload`;
- Alembic migrations run before API startup;
- containers restart `unless-stopped`;
- Docker logs are rotated;
- Nginx terminates public HTTP/HTTPS and proxies to local API.

Start manually on the VPS after creating `.env`:

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

Full guide: [docs/DeploymentVPS.md](docs/DeploymentVPS.md).

## Environment Variables

Copy `.env.example` to `.env` and fill values.

Important production values:

```env
ENVIRONMENT=production
DEBUG=false
APP_NAME=VMmsngrServer
LOG_LEVEL=INFO
ALLOWED_HOSTS=api.<domain>
CORS_ORIGINS=https://api.<domain>

POSTGRES_DB=vmmsngr
POSTGRES_USER=vmmsngr
POSTGRES_PASSWORD=<openssl-rand-hex-32>
DATABASE_URL=postgresql+psycopg2://vmmsngr:<same-password>@db:5432/vmmsngr

JWT_SECRET_KEY=<openssl-rand-hex-64>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
```

Generate secrets:

```bash
openssl rand -hex 32
openssl rand -hex 64
```

When `ENVIRONMENT=production`, the server refuses weak/default secrets, `DEBUG=true`, wildcard hosts and localhost database URLs.

## Deployment

Safe helper:

```bash
scripts/deploy_vps.sh
```

The script checks for `.env`, refuses dirty Git state, pulls with `--ff-only`, builds, applies migrations, starts production compose and waits for `/ready`. It never removes Docker volumes.

Manual update:

```bash
scripts/backup_postgres.sh
git pull --ff-only
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 api
```

## Backup

```bash
scripts/backup_postgres.sh
```

Backups are written to `backups/`, which is ignored by Git. Copy important backups off the VPS.

## Restore

```bash
scripts/restore_postgres.sh backups/vmmsngr-postgres-YYYYMMDDTHHMMSSZ.sql.gz
```

Restore requires typing `RESTORE` and overwrites database data. Create a new backup first.

More details: [docs/Backups.md](docs/Backups.md).

## Troubleshooting

```bash
docker compose config
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 api
docker compose -f docker-compose.prod.yml logs --tail=100 db
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
sudo nginx -t
```

If `/health` works but `/ready` fails, check PostgreSQL health, `DATABASE_URL`, `.env` and Alembic state.

## Useful Local Commands

Run migrations manually:

```bash
docker compose run --rm api alembic upgrade head
```

Create a new migration after model changes:

```bash
docker compose run --rm api alembic revision --autogenerate -m "Describe change"
```

## API Endpoints

### Health

- `GET /health`
- `GET /ready`

### Auth

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Users

- `PATCH /api/v1/users/me`
- `DELETE /api/v1/users/me`

### Devices

- `POST /api/v1/devices/register`
- `PATCH /api/v1/devices/token`
- `DELETE /api/v1/devices/current`

### Pairs

- `POST /api/v1/pairs`
- `POST /api/v1/pairs/join`
- `GET /api/v1/pairs/me`
- `GET /api/v1/pairs/me/partner`
- `POST /api/v1/pairs/leave`
- `DELETE /api/v1/pairs/me`

### Tasks

- `GET /api/v1/tasks`
- `POST /api/v1/tasks`
- `PATCH /api/v1/tasks/{task_id}`
- `DELETE /api/v1/tasks/{task_id}`

### Messages

- `GET /api/v1/messages`
- `POST /api/v1/messages`

### WebSocket

- `GET /api/v1/ws?token=<access_token>`

Do not log WebSocket query tokens.

## Production Notes

- See [docs/ProductionReadiness.md](docs/ProductionReadiness.md).
- See [docs/DeploymentVPS.md](docs/DeploymentVPS.md).
- See [docs/Backups.md](docs/Backups.md).
