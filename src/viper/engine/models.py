"""Pydantic schemas and models for pipelines, stages, and runs."""

from collections.abc import Callable
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Execution status of a pipeline run or individual stage."""

    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'


class PipelineInput(BaseModel):
    """Specification of an external input parameter for a pipeline."""

    name: str
    type: str = 'string'
    label: str | None = None
    required: bool = True
    default: Any = None


class PipelineStageConfig(BaseModel):
    """Configuration and input bindings for a stage node in a DAG."""

    id: str
    stage: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class PipelineManifest(BaseModel):
    """Pipeline definition file schema defining both UX and DAG execution."""

    id: str
    name: str
    description: str = ''
    stages: list[PipelineStageConfig] = Field(default_factory=list)
    inputs: list[PipelineInput] = Field(default_factory=list)
    builtin: bool = False
    icon: str = 'bolt'
    tags: list[str] = Field(default_factory=list)


class StageDefinition(BaseModel):
    """Metadata describing a registered processing stage."""

    name: str
    description: str = ''
    inputs: dict[str, Any] = Field(default_factory=dict)
    fn: Callable[..., Any] | None = None

    model_config = {'arbitrary_types_allowed': True}


class RunResult(BaseModel):
    """Outcome of a pipeline execution run."""

    run_id: str | None = None
    status: RunStatus
    stage_results: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
