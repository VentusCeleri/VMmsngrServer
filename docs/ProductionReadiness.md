# Production Readiness

v1.5 prepares VMmsngrServer for safer VPS operation behind Nginx and HTTPS. It does not perform the VPS changes automatically.

## Current Production Baseline

- FastAPI runs in Docker.
- PostgreSQL runs in Docker.
- Nginx should be the only public HTTP(S) entrypoint.
- PostgreSQL must not be exposed to the internet.
- API port `8000` must be bound only to `127.0.0.1` in production.
- WebSocket, Presence and APNs remain single-process features.

## Configuration

All runtime configuration must come from environment variables or `.env`:

- `APP_NAME`
- `ENVIRONMENT`
- `DEBUG`
- `DATABASE_URL`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `CORS_ORIGINS`
- `ALLOWED_HOSTS`
- `LOG_LEVEL`
- `RATE_LIMIT_*`
- `APNS_*`

When `ENVIRONMENT=production`, startup validation rejects:

- `DEBUG=true`;
- missing, default or short `JWT_SECRET_KEY`;
- `DATABASE_URL` pointing to `localhost`, `127.0.0.1` or `::1`;
- missing/default/short `POSTGRES_PASSWORD`;
- wildcard `ALLOWED_HOSTS=*`.

## Security Baseline

- Passwords are hashed with bcrypt through passlib.
- `bcrypt<5` is pinned because passlib 1.7.4 is not compatible with bcrypt 5.x.
- Refresh tokens are stored by token id and can be revoked on logout.
- Access tokens remain valid until their short TTL expires.
- SQL access goes through SQLAlchemy ORM.
- Pair, task and message access is scoped to the authenticated user's pair.
- Pair deletion, pair leave and account deletion run in database transactions and roll back on database errors.
- WebSocket pair and user identity are derived from the access token.
- Device token registration requires JWT and is scoped to current user.

## Logging

Production logs should include:

- app startup and shutdown;
- migration output;
- database errors;
- HTTP errors;
- auth failures without sensitive values;
- WebSocket connect/disconnect;
- push provider errors.

Production logs must not include:

- passwords;
- access tokens;
- refresh tokens;
- WebSocket query tokens;
- message bodies;
- task contents;
- `.env` values;
- APNs private key material.

Docker log rotation is configured in `docker-compose.prod.yml` with `max-size=10m` and `max-file=5`.

## Health and Readiness

- `/health`: API process is alive; intentionally lightweight.
- `/ready`: PostgreSQL is reachable and Alembic version table exists.

Nginx can proxy `/health`; Docker healthcheck uses `/ready`.

## Graceful Shutdown

Production compose sets `stop_grace_period: 30s` for the API. FastAPI lifespan logs shutdown, closes active WebSocket connections and disposes the SQLAlchemy engine.

## Rate Limiting

Current rate limiting is in-memory and single-process. It protects MVP endpoints but is not enough for multi-process or multi-node deployment.

Before multi-process deployment, move rate limiting to Redis or the reverse proxy.

## Presence

Presence is approximate:

- online means at least one active WebSocket connection for the user;
- offline is detected after the last connection disconnects;
- PostgreSQL stores only `last_seen_at`;
- no persistent `online=true` column exists.

Current presence is single-process because the connection manager is in-memory. Multi-process deployment requires Redis Pub/Sub or another shared connection/event layer.

## Push Notifications

- APNs is used only as a notification channel.
- WebSocket remains the realtime sync mechanism.
- Push is skipped when the recipient has an active WebSocket connection.
- APNs requires Apple Developer Push Notifications capability, provisioning profile support and APNs Auth Key.
- If APNs is not configured, notification send is skipped and logged.
- Multi-process deployment needs shared presence before push skip decisions are reliable.

## Destructive Operations

- `DELETE /api/v1/pairs/me` hard-deletes pair messages and tasks before deleting the pair.
- `POST /api/v1/pairs/leave` clears the current user's pair slot and deletes the pair only if both slots are empty.
- `DELETE /api/v1/users/me` removes refresh tokens and personal data before deleting the user.

Create backups before production changes and before any manual destructive operation.

## Backups

See `docs/Backups.md`.
