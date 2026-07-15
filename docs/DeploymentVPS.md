# VPS Deployment Guide

This guide prepares VMmsngrServer for a VPS behind Nginx and HTTPS. Do not treat the current public HTTP endpoint as production-safe.

Example VPS IPv4: `72.56.7.75`.

## 1. Domain and DNS

1. Buy or choose a domain.
2. Create a DNS A-record:

```text
api.<domain> -> 72.56.7.75
```

3. Wait for DNS propagation:

```bash
dig api.<domain>
```

## 2. Prepare Environment

On the VPS:

```bash
cd /opt/vmmsngr/VMmsngrServer
cp .env.example .env
```

Generate secrets:

```bash
openssl rand -hex 32
openssl rand -hex 64
```

Fill production values:

```env
ENVIRONMENT=production
DEBUG=false
ALLOWED_HOSTS=api.<domain>
CORS_ORIGINS=https://api.<domain>
POSTGRES_DB=vmmsngr
POSTGRES_USER=vmmsngr
POSTGRES_PASSWORD=<openssl-rand-hex-32>
DATABASE_URL=postgresql+psycopg2://vmmsngr:<same-password>@db:5432/vmmsngr
JWT_SECRET_KEY=<openssl-rand-hex-64>
```

Do not commit `.env`.

## 3. Production Docker

Build and start:

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

Check:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

Production compose:

- keeps PostgreSQL private inside the Docker network;
- binds API only to `127.0.0.1:8000`;
- applies Alembic migrations before API startup;
- does not mount source code into the container;
- does not run Uvicorn with `--reload`;
- rotates Docker logs.

## 4. Install Nginx

```bash
sudo apt update
sudo apt install nginx
```

Copy the example:

```bash
sudo cp deploy/nginx/vmmsngr.conf.example /etc/nginx/sites-available/vmmsngr
sudo sed -i 's/api.example.com/api.<domain>/g' /etc/nginx/sites-available/vmmsngr
sudo ln -s /etc/nginx/sites-available/vmmsngr /etc/nginx/sites-enabled/vmmsngr
sudo nginx -t
sudo systemctl reload nginx
```

## 5. HTTPS With Certbot

Install Certbot:

```bash
sudo apt install certbot python3-certbot-nginx
```

Issue certificate:

```bash
sudo certbot --nginx -d api.<domain>
```

Verify:

```bash
curl https://api.<domain>/health
curl https://api.<domain>/ready
```

Verify WebSocket from a client with a valid access token:

```text
wss://api.<domain>/api/v1/ws?token=<access_token>
```

Do not hardcode certificate paths before Certbot creates them.

## 6. Firewall

Enable UFW only after allowing SSH:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

Do not allow public `5432/tcp` or `8000/tcp`.

If your provider has a Cloud Firewall, make sure it allows:

- `22/tcp`;
- `80/tcp`;
- `443/tcp`.

It should not expose:

- `5432/tcp`;
- `8000/tcp`.

## 7. iOS Switch

After HTTPS works, switch iOS config to:

```xcconfig
OWN_SERVER_BASE_URL = https:/$()/api.<domain>
OWN_SERVER_BASE_API_URL = $(OWN_SERVER_BASE_URL)
```

Then remove temporary arbitrary HTTP allowances from iOS ATS configuration.

## 8. Update

Safe manual update sequence:

```bash
cd /opt/vmmsngr/VMmsngrServer
scripts/backup_postgres.sh
git pull --ff-only
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 api
curl http://127.0.0.1:8000/ready
```

`scripts/deploy_vps.sh` automates the same safe shape and never removes Docker volumes.

## 9. Rollback

Rollback is manual and not zero-downtime on a single API instance:

1. Create a fresh backup.
2. Choose the previous Git commit.
3. Check whether Alembic migrations changed.
4. Rebuild and restart API.

Example:

```bash
scripts/backup_postgres.sh
git checkout <previous-commit>
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

Do not run Alembic downgrade automatically. Database downgrades can lose data or break newer records.

## 10. Troubleshooting

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 api
docker compose -f docker-compose.prod.yml logs --tail=100 db
sudo nginx -t
sudo journalctl -u nginx --no-pager --tail=100
```

If `/health` works but `/ready` fails, inspect PostgreSQL connectivity and Alembic state.
