import time
import traceback
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.jobs.filecopy import run_filecopy_job
from app.jobs.s3 import run_s3_job
from app.jobs.sql import run_sql_backup
from app.models import BackupType, Job, JobRun, RunStatus
from app.notifications import notify_job_run

_DISPATCH = {
    BackupType.sql: run_sql_backup,
    BackupType.s3: run_s3_job,
    BackupType.filecopy: run_filecopy_job,
}


def execute_job(db: Session, job_id: int, job_run_id: int) -> JobRun:
    job = db.get(Job, job_id)
    if job is None:
        raise ValueError(f"job {job_id} not found")

    job_run = db.get(JobRun, job_run_id)
    if job_run is None:
        raise ValueError(f"job run {job_run_id} not found")

    log: list[str] = []
    start = time.monotonic()
    handler = _DISPATCH.get(job.backup_type)

    try:
        if handler is None:
            raise ValueError(f"unsupported backup type: {job.backup_type}")
        handler(job, log)
        job_run.status = RunStatus.success
    except Exception:
        log.append(traceback.format_exc())
        job_run.status = RunStatus.failed
    finally:
        job_run.ended_at = datetime.now(timezone.utc)
        job_run.duration_seconds = time.monotonic() - start
        job_run.log_output = "\n".join(log)
        db.add(job_run)
        db.commit()
        db.refresh(job_run)

    notify_job_run(db, job, job_run)
    return job_run
