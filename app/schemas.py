from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import BackupType, DestinationType, RunStatus, SourceType


class LoginRequest(BaseModel):
    username: str
    password: str


class JobCreate(BaseModel):
    name: str
    description: str | None = None
    source_type: SourceType
    source_config: dict = {}
    destination_type: DestinationType
    destination_config: dict = {}
    backup_type: BackupType
    backup_config: dict = {}
    notify_on_success: bool = False
    enabled: bool = True


class JobUpdate(JobCreate):
    pass


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    source_type: SourceType
    source_config: dict
    destination_type: DestinationType
    destination_config: dict
    backup_type: BackupType
    backup_config: dict
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
