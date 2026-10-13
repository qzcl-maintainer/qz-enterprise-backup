# Backup Application — Backlog

Future features and enhancements not included in the initial build. Items are grouped by category and loosely prioritized within each group (top = highest priority).

---

## Scheduling

- [ ] **Cron-based job scheduling** — define a cron expression per job; a scheduler (APScheduler or Celery Beat) triggers runs automatically
- [ ] **Schedule UI** — visual cron builder in the job form (e.g. "every day at 2am") rather than raw cron syntax
- [ ] **Next-run preview** — show the next scheduled execution time on the Jobs list
- [ ] **Scheduled run history** — distinguish between manual and scheduled runs in the History view
- [ ] **Timezone support** — per-user or per-job timezone setting for scheduled runs

---

## Notifications

- [ ] **Multiple recipients per job** — comma-separated or list of `NOTIFY_TO` addresses
- [ ] **Per-job notification settings** — override global SMTP settings at the job level
- [ ] **Slack webhook notifications** — post job status to a Slack channel
- [ ] **Webhook/HTTP callback** — call a configurable URL on job completion or failure
- [ ] **Notification digest** — daily summary email of all job statuses instead of per-run emails
- [ ] **In-app notification center** — dedicated page listing all past notifications with read/unread state

---

## Authentication & Access Control

- [ ] **Multiple user accounts** — store users in SQLite with hashed passwords
- [ ] **Role-based access control (RBAC)** — Admin (full access), Operator (run jobs, view logs), Viewer (read-only)
- [ ] **API key support** — generate API keys for headless/scripted job triggering
- [ ] **OAuth2 / SSO integration** — login via Google, GitHub, or LDAP
- [ ] **Two-factor authentication (2FA)**

---

## S3 & Cloud Storage

- [ ] **Per-job S3 credential override** — UI fields to supply a different access key/secret per job instead of only the global `.env` credentials
- [ ] **Multiple S3 profiles** — manage named credential profiles, selectable per job
- [ ] **S3-compatible storage** — support MinIO, Backblaze B2, Cloudflare R2, Wasabi via custom endpoint URL
- [ ] **Azure Blob Storage destination**
- [ ] **Google Cloud Storage destination**

---

## Retention & Cleanup

- [ ] **Backup retention policies** — auto-delete old backup files after N days or after N copies (per job)
- [ ] **Log retention UI** — manage `LOG_RETENTION_DAYS` from the UI without editing `.env`
- [ ] **S3 lifecycle rule management** — configure S3 object lifecycle policies from within the app
- [ ] **Storage usage dashboard** — show disk usage for local destinations and object count/size for S3

---

## Job Management

- [ ] **Job dependency chains** — run Job B only after Job A succeeds
- [ ] **Job groups / tags** — organize jobs by environment, server, or type
- [ ] **Duplicate job** — clone an existing job as a starting point for a new one
- [ ] **Dry-run mode** — simulate a job without writing any files
- [ ] **Job enable/disable toggle** — temporarily disable a job without deleting it
- [ ] **Bulk actions** — select multiple jobs to run, enable, disable, or delete at once

---

## Logging & Monitoring

- [ ] **Log search** — full-text search across log output for a job or date range
- [ ] **Log download** — export a run's log as a `.txt` file
- [ ] **Metrics dashboard** — charts for job success rate, average duration, failure trends over time
- [ ] **Health check endpoint** — `/health` route for uptime monitoring tools
- [ ] **External log shipping** — forward logs to syslog, Loki, or an HTTP endpoint

---

## Infrastructure & Deployment

- [ ] **HTTPS / TLS support** — built-in Caddy or nginx reverse proxy with Let's Encrypt
- [ ] **Traefik integration** — labels in `docker-compose.yml` for automatic routing and TLS
- [ ] **Kubernetes manifests** — Helm chart or raw YAML for K8s deployment
- [ ] **Migrate SQLite → PostgreSQL** — optional external DB for high-availability setups
- [ ] **Backup the backup app** — export job definitions and run history as a JSON snapshot

---

## Developer / Extensibility

- [ ] **Plugin system for backup types** — drop a Python module into a `plugins/` directory to add a new backup type without modifying core code
- [ ] **REST API documentation** — auto-generated OpenAPI/Swagger UI at `/docs`
- [ ] **CLI tool** — `backup-cli run <job-name>` for scripting and CI pipelines
- [ ] **Import/export job definitions** — JSON export of all jobs for migration or version control
- [ ] **Audit log** — record who triggered each job and what config changes were made
