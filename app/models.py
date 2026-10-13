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


class DbEngine(str, enum.Enum):
    postgresql = "postgresql"
    mysql = "mysql"
    mssql = "mssql"


class StorageLocation(Base):
    """A reusable, named source/destination endpoint (local path, NFS/SMB share, or S3 bucket)."""

    __tablename__ = "storage_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    location_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DatabaseConnection(Base):
    """A reusable, named database connection for SQL backup jobs."""

    __tablename__ = "database_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    engine: Mapped[DbEngine] = mapped_column(Enum(DbEngine), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    database: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ad hoc source/destination — ignored once the matching *_location_id below is set.
    source_type: Mapped[SourceType | None] = mapped_column(Enum(SourceType), nullable=True)
    source_config: Mapped[dict] = mapped_column(JSON, default=dict)

    destination_type: Mapped[DestinationType | None] = mapped_column(Enum(DestinationType), nullable=True)
    destination_config: Mapped[dict] = mapped_column(JSON, default=dict)

    source_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=True
    )
    destination_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=True
    )

    backup_type: Mapped[BackupType] = mapped_column(Enum(BackupType), nullable=False)
    # Ad hoc DB connection fields (sql jobs) live here too — ignored once database_connection_id is set.
    backup_config: Mapped[dict] = mapped_column(JSON, default=dict)
    database_connection_id: Mapped[int | None] = mapped_column(
        ForeignKey("database_connections.id"), nullable=True
    )

    notify_on_success: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[list["JobRun"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    source_location: Mapped[StorageLocation | None] = relationship(foreign_keys=[source_location_id])
    destination_location: Mapped[StorageLocation | None] = relationship(foreign_keys=[destination_location_id])
    database_connection: Mapped[DatabaseConnection | None] = relationship()

    @property
    def effective_source_type(self) -> SourceType | None:
        return self.source_location.location_type if self.source_location else self.source_type

    @property
    def effective_source_config(self) -> dict:
        return self.source_location.config if self.source_location else (self.source_config or {})

    @property
    def effective_destination_type(self) -> DestinationType | None:
        return self.destination_location.location_type if self.destination_location else self.destination_type

    @property
    def effective_destination_config(self) -> dict:
        return self.destination_location.config if self.destination_location else (self.destination_config or {})

    @property
    def effective_backup_config(self) -> dict:
        cfg = dict(self.backup_config or {})
        if self.backup_type == BackupType.sql and self.database_connection:
            conn = self.database_connection
            cfg = {
                "engine": conn.engine,
                "host": conn.host,
                "port": conn.port,
                "database": conn.database,
                "username": conn.username,
                "password": conn.password,
                **{k: v for k, v in cfg.items() if k == "output_format"},
            }
        return cfg

    @property
    def source_location_name(self) -> str | None:
        return self.source_location.name if self.source_location else None

    @property
    def destination_location_name(self) -> str | None:
        return self.destination_location.name if self.destination_location else None

    @property
    def database_connection_name(self) -> str | None:
        return self.database_connection.name if self.database_connection else None


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
