# Backups

VMmsngrServer stores durable data in PostgreSQL. In local Docker Compose this data lives in the `postgres_data` Docker volume.

## Local Backup

Create a compressed SQL backup:

```bash
docker compose exec db pg_dump -U vmmsngr -d vmmsngr | gzip > vmmsngr-backup.sql.gz
```

## Local Restore

Restore into the local development database:

```bash
gunzip -c vmmsngr-backup.sql.gz | docker compose exec -T db psql -U vmmsngr -d vmmsngr
```

For destructive restore tests, use a separate database or disposable Docker volume.

## Production Recommendation

- Run `pg_dump` at least daily for a family-use VPS.
- Store backups outside the VPS, for example another provider or encrypted local storage.
- Keep several restore points, not only the latest file.
- Test restore regularly. A backup that has never been restored is only a hope.
- Do not include `.env`, JWT secrets or future API secrets in database backups.

## Volumes

Current Docker Compose volume:

```text
postgres_data
```

This volume contains PostgreSQL data files. Losing it without a backup means losing users, pairs, tasks and messages.
