import enum

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class SourceType(str, enum.Enum):
    local = "local"
    nfs = "nfs"
    smb = "smb"
    s3 = "s3"


class DestinationType(str, enum.Enum):
    local = "local"
    nfs = "nfs"
    smb = "smb"
    s3 = "s3"


class BackupType(str, enum.Enum):
    sql = "sql"
    s3 = "s3"
    filecopy = "filecopy"


class RunStatus(str, enum.Enum):
    running = "running"
    success = "success"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_config: Mapped[dict] = mapped_column(JSON, default=dict)

    destination_type: Mapped[DestinationType] = mapped_column(Enum(DestinationType), nullable=False)
    destination_config: Mapped[dict] = mapped_column(JSON, default=dict)

    backup_type: Mapped[BackupType] = mapped_column(Enum(BackupType), nullable=False)
    backup_config: Mapped[dict] = mapped_column(JSON, default=dict)

    notify_on_success: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[list["JobRun"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)

    started_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)

    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.running)
    log_output: Mapped[str] = mapped_column(Text, default="")

    job: Mapped[Job] = relationship(back_populates="runs")
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="job_run", cascade="all, delete-orphan"
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_run_id: Mapped[int] = mapped_column(ForeignKey("job_runs.id"), nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="info")
    read: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job_run: Mapped[JobRun] = relationship(back_populates="notifications")
