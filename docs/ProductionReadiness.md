# Production Readiness Notes

v1.4 prepares VMmsngrServer for a future VPS deployment, but does not deploy production infrastructure yet.

## Configuration

All runtime configuration must come from environment variables or `.env`:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `CORS_ORIGINS`
- `ENVIRONMENT`
- `DEBUG`
- `LOG_LEVEL`
- `ALLOWED_HOSTS`
- rate limit settings
- APNs settings

Production refuses to start with the default weak `JWT_SECRET_KEY` or `DEBUG=true`.

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
- Do not log passwords, access tokens, refresh tokens, WebSocket query strings or message bodies.
- Do not log full APNs tokens or APNs private key paths in production logs.

## Rate Limiting

Current rate limiting is in-memory and single-process. It protects MVP endpoints but is not enough for a multi-process or multi-node deployment.

Protected endpoint groups:

- register/login/refresh;
- pair join;
- sending messages.

Before multi-process deployment, move rate limiting to Redis or a reverse proxy.

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
- Add audit logging and backup/restore review before exposing these operations beyond the family MVP.

## Readiness

- `/health` means the API process is alive.
- `/ready` checks PostgreSQL and the Alembic version table.

## Backups

See `docs/Backups.md`.
