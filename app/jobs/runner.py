import time
import traceback
from datetime import datetime, timezone
from types import SimpleNamespace

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


def _effective_job(job: Job) -> SimpleNamespace:
    """Job handlers only ever read these attributes — resolve saved locations/connections here
    so the handlers themselves don't need to know whether a field was ad hoc or saved."""
    if job.effective_source_type is None:
        raise ValueError("job has no source configured (neither a saved location nor inline fields)")
    if job.effective_destination_type is None:
        raise ValueError("job has no destination configured (neither a saved location nor inline fields)")

    return SimpleNamespace(
        name=job.name,
        backup_type=job.backup_type,
        source_type=job.effective_source_type,
        source_config=job.effective_source_config,
        destination_type=job.effective_destination_type,
        destination_config=job.effective_destination_config,
        backup_config=job.effective_backup_config,
    )


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
        handler(_effective_job(job), log)
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
