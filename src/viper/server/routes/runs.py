"""Pipeline execution run API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from viper.db.models import Run, StageRun
from viper.db.repositories import RunRepository, StageRunRepository
from viper.db.session import get_session

router = APIRouter(prefix='/api/runs', tags=['runs'])


class RunDetailResponse(BaseModel):
    """Run details including associated stage execution records."""

    id: str
    pipeline_id: str
    status: str
    inputs: str
    outputs: str
    created_at: datetime
    finished_at: datetime | None = None
    stage_runs: list[StageRun] = []


@router.get('', response_model=list[Run])
async def list_runs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[Run]:
    """List execution runs ordered chronologically descending."""
    repo = RunRepository(session)
    return await repo.list(limit=limit, offset=offset)


@router.get('/{run_id}', response_model=RunDetailResponse)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> RunDetailResponse:
    """Retrieve execution run details and stage progression by run ID."""
    run_repo = RunRepository(session)
    stage_repo = StageRunRepository(session)

    run = await run_repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found",
        )

    stage_runs = await stage_repo.list_by_run(run_id)
    return RunDetailResponse(
        id=run.id,
        pipeline_id=run.pipeline_id,
        status=run.status,
        inputs=run.inputs,
        outputs=run.outputs,
        created_at=run.created_at,
        finished_at=run.finished_at,
        stage_runs=stage_runs,
    )
