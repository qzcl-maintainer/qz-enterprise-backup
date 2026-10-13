import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app import auth
from app.database import SessionLocal, get_db, init_db
from app.jobs.runner import execute_job
from app.models import Job, JobRun, Notification
from app.schemas import (
    JobCreate,
    JobOut,
    JobRunDetailOut,
    JobRunOut,
    JobUpdate,
    LoginRequest,
    NotificationOut,
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(title="Backup Management App")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-secret-change-me"),
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    _purge_old_logs()


def _purge_old_logs() -> None:
    retention_days = int(os.environ.get("LOG_RETENTION_DAYS", "30"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    db = SessionLocal()
    try:
        db.query(JobRun).filter(JobRun.started_at < cutoff).delete()
        db.commit()
    finally:
        db.close()


# ---------- Auth ----------


@app.post("/auth/login")
def login(payload: LoginRequest, request: Request):
    if not auth.check_credentials(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    auth.login(request, payload.username)
    return {"ok": True}


@app.post("/auth/logout")
def logout(request: Request):
    auth.logout(request)
    return {"ok": True}


@app.get("/auth/me")
def me(request: Request):
    return {"user": auth.current_user(request)}


# ---------- Jobs ----------


@app.get("/api/jobs", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), user: str = Depends(auth.require_auth)):
    return db.query(Job).order_by(Job.created_at.desc()).all()


@app.post("/api/jobs", response_model=JobOut, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db), user: str = Depends(auth.require_auth)):
    job = Job(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@app.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db), user: str = Depends(auth.require_auth)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.put("/api/jobs/{job_id}", response_model=JobOut)
def update_job(
    job_id: int,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    user: str = Depends(auth.require_auth),
):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    for field, value in payload.model_dump().items():
        setattr(job, field, value)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db), user: str = Depends(auth.require_auth)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return JSONResponse(status_code=204, content=None)


def _run_job_background(job_id: int, job_run_id: int) -> None:
    db = SessionLocal()
    try:
        execute_job(db, job_id, job_run_id)
    finally:
        db.close()


@app.post("/api/jobs/{job_id}/run", response_model=JobRunOut, status_code=202)
def run_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: str = Depends(auth.require_auth),
):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    job_run = JobRun(job_id=job.id)
    db.add(job_run)
    db.commit()
    db.refresh(job_run)

    background_tasks.add_task(_run_job_background, job_id, job_run.id)
    return job_run


# ---------- History & Logs ----------


@app.get("/api/runs", response_model=list[JobRunOut])
def list_runs(
    job_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    user: str = Depends(auth.require_auth),
):
    query = db.query(JobRun)
    if job_id is not None:
        query = query.filter(JobRun.job_id == job_id)
    if status_filter is not None:
        query = query.filter(JobRun.status == status_filter)
    return query.order_by(JobRun.started_at.desc()).all()


@app.get("/api/runs/{run_id}", response_model=JobRunDetailOut)
def get_run(run_id: int, db: Session = Depends(get_db), user: str = Depends(auth.require_auth)):
    run = db.get(JobRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/api/runs/{run_id}/logs")
def get_run_logs(run_id: int, db: Session = Depends(get_db), user: str = Depends(auth.require_auth)):
    run = db.get(JobRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"log_output": run.log_output}


# ---------- Notifications ----------


@app.get("/api/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    user: str = Depends(auth.require_auth),
):
    query = db.query(Notification)
    if unread_only:
        query = query.filter(Notification.read == False)  # noqa: E712
    return query.order_by(Notification.created_at.desc()).all()


@app.post("/api/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(auth.require_auth),
):
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read = True
    db.add(notification)
    db.commit()
    return {"ok": True}


# ---------- Static frontend ----------

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/login")
def login_page():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
