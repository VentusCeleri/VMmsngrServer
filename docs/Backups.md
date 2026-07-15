# Backups

VMmsngrServer stores durable data in PostgreSQL. In Docker this data lives in the `postgres_data` named volume.

Backups on the same VPS protect against accidental application mistakes, but they do not protect against VPS loss. Copy important backups to another storage provider or encrypted local storage.

## Production Backup

Create a timestamped compressed SQL backup:

```bash
cd /opt/vmmsngr/VMmsngrServer
scripts/backup_postgres.sh
```

The script:

- uses `docker compose -f docker-compose.prod.yml exec db pg_dump`;
- reads database settings from the running container environment;
- does not store a password in the script;
- creates `backups/`;
- writes a timestamped `.sql.gz` file;
- sets restrictive file permissions.

## Production Restore

Restore requires an explicit backup path and confirmation:

```bash
cd /opt/vmmsngr/VMmsngrServer
scripts/restore_postgres.sh backups/vmmsngr-postgres-YYYYMMDDTHHMMSSZ.sql.gz
```

Restore overwrites data in the configured database. Create a fresh backup before restoring:

```bash
scripts/backup_postgres.sh
```

## Daily Cron Example

```cron
15 3 * * * cd /opt/vmmsngr/VMmsngrServer && scripts/backup_postgres.sh >> /var/log/vmmsngr-backup.log 2>&1
```

Move resulting backups away from the VPS regularly, for example with `scp`, `rsync`, restic or another encrypted backup tool.

## Local Backup

```bash
docker compose exec db pg_dump -U vmmsngr -d vmmsngr | gzip > vmmsngr-backup.sql.gz
```

## Local Restore

```bash
gunzip -c vmmsngr-backup.sql.gz | docker compose exec -T db psql -U vmmsngr -d vmmsngr
```

For destructive restore tests, use a separate database or disposable Docker volume.

## Safe Password Rotation

Do not change `POSTGRES_PASSWORD` for an existing Docker volume only in `.env`: PostgreSQL will not automatically change the existing database user's password.

Safe sequence:

1. Create a backup.
2. Generate a new password:

```bash
openssl rand -hex 32
```

3. Change the database user's password inside PostgreSQL:

```bash
docker compose -f docker-compose.prod.yml exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "alter user \"$POSTGRES_USER\" with password 'NEW_PASSWORD';"
```

4. Update `.env`:

```env
POSTGRES_PASSWORD=NEW_PASSWORD
DATABASE_URL=postgresql+psycopg2://USER:NEW_PASSWORD@db:5432/DB
```

5. Restart the API and confirm `/ready`.

Never commit `.env` or generated backups.
