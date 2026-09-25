"""Database models using SQLModel for tables and Pydantic schemas."""

import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _generate_uuid() -> str:
    return uuid.uuid4().hex


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Run(SQLModel, table=True):
    """Pipeline execution run record."""

    id: str = Field(default_factory=_generate_uuid, primary_key=True)
    pipeline_id: str = Field(index=True)
    status: str = Field(default='pending', index=True)
    inputs: str = Field(default='{}')
    outputs: str = Field(default='{}')
    created_at: datetime = Field(default_factory=_utc_now)
    finished_at: datetime | None = Field(default=None)


class StageRun(SQLModel, table=True):
    """Individual stage execution result within a run."""

    id: str = Field(default_factory=_generate_uuid, primary_key=True)
    run_id: str = Field(foreign_key='run.id', index=True)
    stage_id: str = Field(index=True)
    status: str = Field(default='pending', index=True)
    output: str = Field(default='{}')
    error: str | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)


class Asset(SQLModel, table=True):
    """Persisted asset artifact created by a pipeline or stage."""

    id: str = Field(default_factory=_generate_uuid, primary_key=True)
    run_id: str | None = Field(default=None, foreign_key='run.id', index=True)
    stage_id: str | None = Field(default=None)
    asset_type: str = Field(index=True)
    path: str
    metadata_json: str = Field(default='{}')
    created_at: datetime = Field(default_factory=_utc_now)
