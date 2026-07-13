# VMmsngrServer

Local MVP backend for VMmsngr, a private family messenger and organizer for two people.

## Stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- JWT auth
- Docker Compose for local development

No production deploy, WebSocket, push notifications, AI, or file storage are included in this MVP.

## Project Structure

```text
VMmsngrServer/
  app/
    api/routes/       HTTP endpoints
    core/             config, security, error handling
    db/               SQLAlchemy session/base
    models/           SQLAlchemy models
    schemas/          Pydantic request/response models
    services/         small domain helpers
    main.py           FastAPI app factory
  alembic/
    versions/         database migrations
  docker-compose.yml
  Dockerfile
  requirements.txt
```

## Local Run With Docker Compose

```bash
cd VMmsngrServer
cp .env.example .env
docker compose up --build
```

The API will be available at:

- API: <http://localhost:8000>
- Health: <http://localhost:8000/health>
- OpenAPI docs: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## Useful Commands

Run migrations manually:

```bash
docker compose run --rm api alembic upgrade head
```

Create a new migration after model changes:

```bash
docker compose run --rm api alembic revision --autogenerate -m "Describe change"
```

Check health:

```bash
curl http://localhost:8000/health
```

## API Endpoints

### Health

- `GET /health`

### Auth

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Pairs

- `POST /api/v1/pairs`
- `POST /api/v1/pairs/join`
- `GET /api/v1/pairs/me`

### Tasks

- `GET /api/v1/tasks`
- `POST /api/v1/tasks`
- `PATCH /api/v1/tasks/{task_id}`
- `DELETE /api/v1/tasks/{task_id}`

### Messages

- `GET /api/v1/messages`
- `POST /api/v1/messages`

## Authorization Rules

- Every protected endpoint requires `Authorization: Bearer <access_token>`.
- Users can only read their own current pair.
- Tasks are always scoped to the authenticated user's pair.
- Messages are always scoped to the authenticated user's pair.
- `assignee_id` and `receiver_id` must belong to the same pair when provided.
- Task deletion is soft delete via `deleted_at`.
- Logout revokes refresh tokens; access tokens remain valid until their normal short expiration.

## Example Flow

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"a@example.com","password":"password123","display_name":"Alex"}'
```

Use the returned `access_token`:

```bash
curl -X POST http://localhost:8000/api/v1/pairs \
  -H "Authorization: Bearer ACCESS_TOKEN"
```
