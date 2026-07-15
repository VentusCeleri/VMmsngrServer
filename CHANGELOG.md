# Changelog

## 2026-07-14 - v1.5 Production Infrastructure Hardening

### Added

- Added `docker-compose.prod.yml` for VPS deployment behind Nginx.
- Added `.dockerignore`.
- Added Nginx reverse proxy example with WebSocket support.
- Added deployment, backup and restore scripts.
- Added VPS deployment, production readiness and backup documentation.
- Added production configuration validation tests and production compose security tests.
- Added GitHub Actions backend CI workflow.

### Changed

- Hardened Dockerfile with non-root runtime user.
- Expanded `.env.example` with production variables.
- Added startup validation for unsafe production settings.
- Added graceful FastAPI shutdown cleanup for WebSockets and database engine.
- Documented Alembic revision chain and production update/rollback flow.
