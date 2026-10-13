# Backup Manager

A lightweight, self-hosted, web-based backup management application. Define, run, and monitor backup jobs through a browser UI — deployed entirely via Docker Compose, no external dependencies beyond Docker.

## Features

- **SQL backups** — PostgreSQL, MySQL, or MSSQL, dumped to `.sql` or `.sql.gz`
- **S3 sync/copy** — upload or download via the AWS CLI, in `copy` or `sync` mode
- **File copy** — `rsync` (with optional `--delete`) or additive-only `xcopy`-style copy
- **Sources & destinations** — local paths, NFS, SMB/CIFS shares, or (for destinations/S3 jobs) Amazon S3
- **Reusable Storage Locations & Database Connections** — save an SMB share, S3 bucket, or DB connection once and reference it from any job instead of re-entering it; updates to a saved location/connection apply to every job using it automatically
- **History & logs** — every run's full stdout/stderr, filterable by job and status
- **Notifications** — in-app + email on failure (optionally also on success, per job)

## Setup

1. Copy `.env.example` to `.env` and fill in values:
   ```sh
   cp .env.example .env
   ```
   At minimum, set `ADMIN_USER`, `ADMIN_PASSWORD`, and `SESSION_SECRET`. Fill in S3/SMTP credentials if you plan to use those features.

2. Start the app:
   ```sh
   docker compose up --build
   ```

3. Open [http://localhost:8080](http://localhost:8080) and log in with your `ADMIN_USER` / `ADMIN_PASSWORD`.

## Notes

- The SQLite database lives at `./data/backup.db` (volume-mounted) — back this up too.
- The host's `/mnt` is mounted into the container at `/mnt`, so "local" source/destination paths for host-mounted drives should live under `/mnt/...`.
- Mounting NFS/CIFS shares from inside the container requires the `SYS_ADMIN` capability and (on AppArmor hosts) `apparmor:unconfined` — both are already set in `docker-compose.yml`.
- Logs older than `LOG_RETENTION_DAYS` (default 30) are purged automatically on startup.
- A Storage Location or Database Connection still referenced by a job can't be deleted — update the job first.
- Database connection passwords are never returned by the API; leave the password field blank when editing a connection to keep the current one.
- See `BACKLOG.md` for planned features not yet included (scheduling, RBAC, retention policies, etc).
