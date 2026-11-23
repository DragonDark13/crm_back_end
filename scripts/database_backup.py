"""Create and restore PostgreSQL custom-format backups.

DATABASE_URL must point to the database being backed up or restored.
The restore command is destructive and requires --confirm-restore.
"""
import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


def database_connection_env(database_url):
    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg2"}:
        raise ValueError("DATABASE_URL must use PostgreSQL.")
    database_name = unquote(parsed.path.lstrip("/"))
    if not database_name:
        raise ValueError("DATABASE_URL must include a database name.")

    env = os.environ.copy()
    if parsed.password is not None:
        env["PGPASSWORD"] = unquote(parsed.password)
    sslmode = parse_qs(parsed.query).get("sslmode", [None])[0]
    if sslmode:
        env["PGSSLMODE"] = sslmode

    connection = ["--dbname", database_name]
    if parsed.hostname:
        connection.extend(["--host", parsed.hostname])
    if parsed.port:
        connection.extend(["--port", str(parsed.port)])
    if parsed.username:
        connection.extend(["--username", unquote(parsed.username)])
    return connection, env


def run_backup(output_dir):
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required.")
    connection, env = database_connection_env(database_url)
    pg_dump = shutil.which("pg_dump")
    pg_restore = shutil.which("pg_restore")
    if not pg_dump or not pg_restore:
        raise RuntimeError("PostgreSQL client tools pg_dump and pg_restore are required.")

    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = output_dir / f"crm-backup-{timestamp}.dump"
    temporary_path = backup_path.with_suffix(".dump.tmp")

    command = [
        pg_dump, *connection, "--format=custom", "--no-owner",
        "--no-privileges", "--file", str(temporary_path),
    ]
    try:
        subprocess.run(command, env=env, check=True)
        if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
            raise RuntimeError("pg_dump produced an empty backup.")
        subprocess.run(
            [pg_restore, "--list", str(temporary_path)],
            env=env, check=True, stdout=subprocess.DEVNULL,
        )
        os.replace(temporary_path, backup_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    print(f"Backup created and archive-checked: {backup_path}")
    return backup_path


def run_restore(backup_file, confirmed):
    if not confirmed:
        raise RuntimeError("Restore not started. Re-run with --confirm-restore after verifying the target database.")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required.")
    connection, env = database_connection_env(database_url)
    pg_restore = shutil.which("pg_restore")
    if not pg_restore:
        raise RuntimeError("PostgreSQL client tool pg_restore is required.")

    backup_path = Path(backup_file).expanduser().resolve()
    if not backup_path.is_file() or backup_path.stat().st_size == 0:
        raise FileNotFoundError(f"Backup file does not exist or is empty: {backup_path}")

    command = [
        pg_restore, *connection, "--clean", "--if-exists",
        "--no-owner", "--no-privileges", "--exit-on-error", str(backup_path),
    ]
    subprocess.run(command, env=env, check=True)
    print(f"Restore completed from: {backup_path}")


def main():
    parser = argparse.ArgumentParser(description="CRM PostgreSQL backup and restore utility.")
    commands = parser.add_subparsers(dest="command", required=True)
    backup_parser = commands.add_parser("backup", help="Create and validate a database backup.")
    backup_parser.add_argument("--output-dir", default="backups")
    restore_parser = commands.add_parser("restore", help="Destructively restore a database backup.")
    restore_parser.add_argument("backup_file")
    restore_parser.add_argument("--confirm-restore", action="store_true")
    args = parser.parse_args()

    try:
        if args.command == "backup":
            run_backup(args.output_dir)
        else:
            run_restore(args.backup_file, args.confirm_restore)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
