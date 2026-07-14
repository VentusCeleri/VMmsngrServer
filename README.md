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
- Docker Compose for local development

No production VPS deploy, AI, Redis, E2E encryption or file storage are included in v1.4.

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
    realtime/         in-memory WebSocket connection manager
    main.py           FastAPI app factory
  alembic/
    versions/         database migrations
  docker-compose.yml
  Dockerfile
  requirements.txt
```

## Local Run With Docker Compose

```bash
cd /Users/mapku3/Documents/VMmsngrServer
cp .env.example .env
docker compose up --build
```

The API will be available at:

- API: <http://localhost:8000>
- Health: <http://localhost:8000/health>
- Readiness: <http://localhost:8000/ready>
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
curl http://localhost:8000/ready
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

Events:

- `connection.ready`
- `message.created`
- `task.created`
- `task.updated`
- `task.deleted`
- `presence.updated`
- `profile.updated`
- `pair.updated`
- `pair.deleted`
- `user.left`
- `error`
- `ping`
- `pong`

## Authorization Rules

- Every protected endpoint requires `Authorization: Bearer <access_token>`.
- Users can only read their own current pair.
- Users can leave their pair; the server clears their participant slot.
- Users can delete their pair; the server deletes pair messages and tasks first.
- Users can delete their account; the server revokes refresh tokens and removes personal data in one transaction.
- Tasks are always scoped to the authenticated user's pair.
- Messages are always scoped to the authenticated user's pair.
- `assignee_id` and `receiver_id` must belong to the same pair when provided.
- Task deletion is soft delete via `deleted_at`.
- Logout revokes refresh tokens; access tokens remain valid until their normal short expiration.
- Presence is derived from active WebSocket connections, not a persistent `online` boolean.
- PostgreSQL stores `last_seen_at` only.
- WebSocket events are pair-scoped.
- Push notifications are sent only to users without an active WebSocket connection.
- If APNs is not configured, push send is skipped with an INFO log while message/task writes continue.

## APNs Configuration

Set these values in `.env` only after enabling Push Notifications in Apple Developer:

```env
APNS_ENABLED=true
APNS_ENVIRONMENT=sandbox
APNS_TEAM_ID=
APNS_KEY_ID=
APNS_BUNDLE_ID=com.maxvika.VMmsngr
APNS_PRIVATE_KEY_PATH=/absolute/path/to/AuthKey.p8
```

Do not commit `.p8` files or APNs credentials.

## Profile Model

`email` is used for authentication. `username` is a unique public identifier stored in lowercase. `display_name` is the human-facing name used by iOS UI.

Username rules:

- 3-30 chars;
- latin letters, digits, underscore and dot;
- unique case-insensitively by normalized lowercase value.

## Production Readiness Notes

- Configure all values through `.env`.
- `ENVIRONMENT=production` refuses default or short `JWT_SECRET_KEY`.
- Do not log passwords, access tokens, refresh tokens or WebSocket query strings.
- Rate limiting is in-memory and single-process only.
- Presence is in-memory and single-process only.
- Use `docs/Backups.md` before storing important data on a VPS.

## Example Flow

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"a@example.com","username":"alex","password":"password123","display_name":"Alex"}'
```

Use the returned `access_token`:

```bash
curl -X POST http://localhost:8000/api/v1/pairs \
  -H "Authorization: Bearer ACCESS_TOKEN"
```
