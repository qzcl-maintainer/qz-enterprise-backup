# Backup Management Application — Build Specification

## Overview

A lightweight, self-hosted, web-based backup management application deployed entirely via Docker Compose. Users define, execute, and monitor backup jobs through a browser-based UI with no external dependencies beyond Docker.

---

## Architecture

| Layer | Technology |
|---|---|
| Containerization | Docker Compose |
| Backend | Python 3.11 + FastAPI |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Database | SQLite via SQLAlchemy |
| Config | `.env` file |
| Auth | Single admin user defined in `.env` |

All services run in a single `docker-compose.yml`. The frontend is served by FastAPI (via static files or Jinja2 templates). No external database server required.

---

## Authentication

- Single hardcoded admin user loaded from `.env`
- Session-based login protecting all routes
- Login page served at `/login`
- Env vars: `ADMIN_USER`, `ADMIN_PASSWORD`

---

## Backup Job Configuration

Each job is defined with the following fields:

### Source

| Option | Fields |
|---|---|
| Local | Path on host (mounted into container) |
| Network — NFS | Host, export path, mount options |
| Network — CIFS/SMB | Host, share name, username, password, domain (optional), mount options |

### Destination

| Option | Fields |
|---|---|
| Local | Path on host (mounted into container) |
| Network — NFS | Host, export path, mount options |
| Network — CIFS/SMB | Host, share name, username, password, domain (optional), mount options |
| Amazon S3 | Bucket, prefix/path, region; credentials from `.env` or job-level override |

### Backup Type

#### SQL Backup
Dumps a database to a file, then stores it at the configured destination.

| Field | Details |
|---|---|
| DB Engine | MSSQL, MySQL, or PostgreSQL (selectable per job) |
| Host | Database host |
| Port | Database port |
| Database | Database name |
| Username | DB user |
| Password | DB password |
| Output format | `.sql` dump or compressed `.gz` |

Each engine's driver/client is installed in the container at build time so the application is extensible without code changes.

- MSSQL → `mssql-tools` + `pyodbc`
- MySQL → `mysqldump` + `mysql-connector-python`
- PostgreSQL → `pg_dump` + `psycopg2`

#### S3 Sync / Copy
Transfers files to or from S3 using the AWS CLI (`aws s3 cp` or `aws s3 sync`).

| Field | Details |
|---|---|
| Mode | `copy` (one-time transfer) or `sync` (mirror, removes deleted files) |
| Direction | Upload (local → S3) or Download (S3 → local) |
| Source path | Local path or S3 URI |
| Destination path | S3 URI or local path |

#### File Copy
Copies files between local and/or network paths.

| Field | Details |
|---|---|
| Mode | `xcopy` (Windows-style, additive only) or `rsync` (with optional `--delete` flag) |
| Source | Local or network path |
| Destination | Local or network path |
| Delete removed files | Toggle (rsync only) |

---

## UI Layout — Two Sections

### Section 1: Jobs

- List of all defined backup jobs in a table:
  - Job name, type, source summary, destination summary, last run time, last status badge
- Actions per job: **Edit**, **Delete**, **Run Now**
- **Create Job** button opens a form/modal
- Status badges: `Idle` · `Running` · `Success` · `Failed`
- Status updates in real time via polling or WebSocket

### Section 2: History & Logs

- Table of all job executions:
  - Job name, start time, end time, duration, status
- Filterable by: job name, status, date range
- Click any row → expand an inline **line-by-line log viewer**
  - Displays captured stdout and stderr
  - Monospace font, scrollable, line numbers

---

## Notifications

### In-App
- Toast/banner on job completion or failure
- Status badge updates without page reload (polling or WebSocket)

### Email
- Sent via SMTP on job failure
- Optional: also send on job success (toggled per job)
- Configured entirely in `.env`

---

## Logging

- Each job execution captures full stdout and stderr
- Stored in SQLite (log text) linked to execution record by foreign key
- Viewable line-by-line in the UI log viewer
- Retention period configurable via `LOG_RETENTION_DAYS` in `.env`
- A background task purges logs older than the retention window on app startup and daily thereafter

---

## `.env` File

```dotenv
# Auth
ADMIN_USER=admin
ADMIN_PASSWORD=changeme

# Amazon S3 (global credentials)
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_REGION=us-east-1

# SMTP / Email Notifications
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
NOTIFY_FROM=backup-app@example.com
NOTIFY_TO=admin@example.com
SMTP_TLS=true

# Logging
LOG_RETENTION_DAYS=30
```

Copy `.env.example` to `.env` and fill in values before first run.

---

## Docker Compose Structure

```
backup-app/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .env                  # created by user, git-ignored
├── README.md
├── app/
│   ├── main.py           # FastAPI entry point
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── database.py       # DB connection/session
│   ├── auth.py           # Session auth
│   ├── jobs/
│   │   ├── runner.py     # Subprocess job executor
│   │   ├── sql.py        # SQL dump logic
│   │   ├── s3.py         # S3 copy/sync logic
│   │   └── filecopy.py   # xcopy / rsync logic
│   ├── notifications.py  # Email + in-app notification logic
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js
└── data/
    └── backup.db         # SQLite DB (volume-mounted)
```

### `docker-compose.yml` (outline)

```yaml
services:
  backup-app:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data          # SQLite DB
      - /mnt:/mnt             # Host paths for local/network backups
    env_file:
      - .env
    restart: unless-stopped
```

### `Dockerfile` (outline)

```dockerfile
FROM python:3.11-slim

# Install system tools
RUN apt-get update && apt-get install -y \
    rsync \
    cifs-utils \
    nfs-common \
    awscli \
    postgresql-client \
    default-mysql-client \
    # mssql-tools added separately via Microsoft repo
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## REST API Endpoints (FastAPI)

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | Login with credentials |
| POST | `/auth/logout` | End session |
| GET | `/api/jobs` | List all jobs |
| POST | `/api/jobs` | Create a job |
| GET | `/api/jobs/{id}` | Get job details |
| PUT | `/api/jobs/{id}` | Update a job |
| DELETE | `/api/jobs/{id}` | Delete a job |
| POST | `/api/jobs/{id}/run` | Trigger a job manually |
| GET | `/api/runs` | List all job executions |
| GET | `/api/runs/{id}` | Get execution details |
| GET | `/api/runs/{id}/logs` | Get line-by-line log for a run |
| GET | `/api/notifications` | Get unread in-app notifications |
| POST | `/api/notifications/{id}/read` | Mark notification as read |

---

## SQLite Data Models

### `Job`
- `id`, `name`, `description`
- `source_type` (local / nfs / smb)
- `source_config` (JSON)
- `destination_type` (local / nfs / smb / s3)
- `destination_config` (JSON)
- `backup_type` (sql / s3 / filecopy)
- `backup_config` (JSON)
- `notify_on_success` (bool)
- `created_at`, `updated_at`

### `JobRun`
- `id`, `job_id` (FK)
- `started_at`, `ended_at`, `duration_seconds`
- `status` (running / success / failed)
- `log_output` (text, full captured output)

### `Notification`
- `id`, `job_run_id` (FK)
- `message`, `level` (info / error)
- `read` (bool)
- `created_at`

---

## Deliverables Checklist

- [ ] `docker-compose.yml`
- [ ] `Dockerfile`
- [ ] FastAPI backend (models, routes, job runner, notifications)
- [ ] SQL backup support: MSSQL, MySQL, PostgreSQL
- [ ] S3 copy and sync support
- [ ] File copy: xcopy and rsync modes
- [ ] NFS and CIFS/SMB mount support
- [ ] Vanilla HTML/CSS/JS frontend — Jobs section
- [ ] Vanilla HTML/CSS/JS frontend — History & Logs section
- [ ] Line-by-line log viewer
- [ ] In-app toast notifications with real-time status updates
- [ ] Email notifications via SMTP
- [ ] Session-based auth from `.env`
- [ ] `.env.example`
- [ ] `README.md` with setup instructions
