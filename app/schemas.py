from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import BackupType, DbEngine, DestinationType, RunStatus, SourceType


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------- Storage Locations ----------


class StorageLocationCreate(BaseModel):
    name: str
    description: str | None = None
    location_type: SourceType
    config: dict = {}


class StorageLocationUpdate(StorageLocationCreate):
    pass


class StorageLocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    location_type: SourceType
    config: dict
    created_at: datetime
    updated_at: datetime


# ---------- Database Connections ----------


class DatabaseConnectionCreate(BaseModel):
    name: str
    description: str | None = None
    engine: DbEngine
    host: str
    port: int | None = None
    database: str
    username: str
    password: str


class DatabaseConnectionUpdate(DatabaseConnectionCreate):
    password: str | None = None  # blank means "keep the current password"


class DatabaseConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    engine: DbEngine
    host: str
    port: int | None
    database: str
    username: str
    created_at: datetime
    updated_at: datetime


# ---------- Jobs ----------


class JobCreate(BaseModel):
    name: str
    description: str | None = None

    source_type: SourceType | None = None
    source_config: dict = {}
    source_location_id: int | None = None

    destination_type: DestinationType | None = None
    destination_config: dict = {}
    destination_location_id: int | None = None

    backup_type: BackupType
    backup_config: dict = {}
    database_connection_id: int | None = None

    notify_on_success: bool = False
    enabled: bool = True


class JobUpdate(JobCreate):
    pass


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None

    source_type: SourceType | None
    source_config: dict
    source_location_id: int | None
    source_location_name: str | None

    destination_type: DestinationType | None
    destination_config: dict
    destination_location_id: int | None
    destination_location_name: str | None

    backup_type: BackupType
    backup_config: dict
    database_connection_id: int | None
    database_connection_name: str | None

    notify_on_success: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime


class JobRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: float | None
    status: RunStatus


class JobRunDetailOut(JobRunOut):
    log_output: str


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_run_id: int
    message: str
    level: str
    read: bool
    created_at: datetime
