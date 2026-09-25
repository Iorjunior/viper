"""Pipeline manifest API endpoints."""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from viper.db.models import Run
from viper.db.repositories import RunRepository
from viper.db.session import get_session
from viper.engine.manifest_loader import get_manifest, load_manifests_from_dir
from viper.engine.models import PipelineManifest
from viper.worker.queue import enqueue

router = APIRouter(prefix='/api/pipelines', tags=['pipelines'])


@router.get('', response_model=list[PipelineManifest])
async def list_pipelines() -> list[PipelineManifest]:
    """List all available built-in and custom pipeline manifests."""
    manifests = load_manifests_from_dir()
    return list(manifests.values())


@router.get('/{pipeline_id}', response_model=PipelineManifest)
async def get_pipeline(pipeline_id: str) -> PipelineManifest:
    """Retrieve full pipeline definition and input schemas by ID."""
    manifest = get_manifest(pipeline_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline '{pipeline_id}' not found",
        )
    return manifest


@router.post(
    '/{pipeline_id}/run',
    response_model=Run,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_pipeline_run(
    pipeline_id: str,
    inputs: dict[str, Any],
    session: AsyncSession = Depends(get_session),
) -> Run:
    """Trigger a pipeline execution creating a pending run record."""
    manifest = get_manifest(pipeline_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline '{pipeline_id}' not found",
        )

    run = Run(
        pipeline_id=pipeline_id,
        status='pending',
        inputs=json.dumps(inputs),
    )
    repo = RunRepository(session)
    created = await repo.create(run)
    enqueue(created.id)
    return created
