import os
import smtplib
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.models import Job, JobRun, Notification, RunStatus


def _send_email(subject: str, body: str) -> None:
    host = os.environ.get("SMTP_HOST")
    if not host:
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.environ.get("NOTIFY_FROM", "backup-app@example.com")
    msg["To"] = os.environ.get("NOTIFY_TO", "")

    port = int(os.environ.get("SMTP_PORT", "587"))
    use_tls = os.environ.get("SMTP_TLS", "true").lower() == "true"
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")

    with smtplib.SMTP(host, port) as server:
        if use_tls:
            server.starttls()
        if user and password:
            server.login(user, password)
        server.sendmail(msg["From"], [msg["To"]], msg.as_string())


def notify_job_run(db: Session, job: Job, job_run: JobRun) -> None:
    should_email = job_run.status == RunStatus.failed or (
        job_run.status == RunStatus.success and job.notify_on_success
    )

    message = f"Job '{job.name}' {job_run.status.value} (run #{job_run.id})"
    level = "error" if job_run.status == RunStatus.failed else "info"

    notification = Notification(job_run_id=job_run.id, message=message, level=level)
    db.add(notification)
    db.commit()

    if should_email:
        subject = f"[Backup App] {job.name}: {job_run.status.value}"
        body = f"{message}\n\n--- Log ---\n{job_run.log_output[-4000:]}"
        try:
            _send_email(subject, body)
        except Exception as exc:  # SMTP failures shouldn't crash the job runner
            db.add(
                Notification(
                    job_run_id=job_run.id,
                    message=f"Failed to send email notification: {exc}",
                    level="error",
                )
            )
            db.commit()
