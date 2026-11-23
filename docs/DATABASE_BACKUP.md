# Database backup and restore

The CRM uses PostgreSQL. Git commits and SQL migration files are not database backups.

## Create a backup

1. Set `DATABASE_URL` in the environment to the database that should be backed up.
2. Install PostgreSQL client tools (`pg_dump` and `pg_restore`).
3. From the backend repository root run:

```bash
python scripts/database_backup.py backup
```

The command writes a PostgreSQL custom-format archive to `backups/`, checks that the archive can be listed by `pg_restore`, and only then publishes the final `.dump` file. Keep backups outside the application server as well; a backup stored only on the same machine is not sufficient protection.

## Restore a backup

Restore is destructive: it replaces objects in the target database. First point `DATABASE_URL` at the intended target database and verify it carefully. Then run:

```bash
python scripts/database_backup.py restore backups/your-backup.dump --confirm-restore
```

The restore stops on the first PostgreSQL error. Never test restoration against the live database; use a separate empty/staging database.

## Operational requirement

This utility does not schedule backups. Configure a daily scheduled task (cron, systemd timer, or Windows Task Scheduler) on the server that hosts the database, and copy completed archives to a separate storage location. Periodically restore a backup into a disposable database to verify recoverability. Do not commit backup files or database credentials to Git.
