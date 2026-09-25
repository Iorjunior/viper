"""Asynchronous data access repositories for database entities."""

from datetime import datetime

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from viper.db.models import Asset, Run, StageRun


class RunRepository:
    """Repository handling CRUD operations for pipeline runs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, run: Run) -> Run:
        """Persist a new pipeline run."""
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get(self, run_id: str) -> Run | None:
        """Fetch a run by unique identifier."""
        return await self.session.get(Run, run_id)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> list[Run]:
        """List runs ordered by creation time descending."""
        statement = select(Run)
        if status is not None:
            statement = statement.where(Run.status == status)
        statement = (
            statement
            .order_by(col(Run.created_at).desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.exec(statement)
        return list(result.all())

    async def update_status(
        self,
        run_id: str,
        status: str,
        outputs: str | None = None,
        finished_at: datetime | None = None,
    ) -> Run | None:
        """Update run status and optional outputs/finished timestamp."""
        run = await self.get(run_id)
        if not run:
            return None
        run.status = status
        if outputs is not None:
            run.outputs = outputs
        if finished_at is not None:
            run.finished_at = finished_at
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def delete(self, run_id: str) -> bool:
        """Delete a run by unique identifier."""
        run = await self.get(run_id)
        if not run:
            return False
        await self.session.delete(run)
        await self.session.commit()
        return True


class StageRunRepository:
    """Repository handling stage run execution tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_or_update(self, stage_run: StageRun) -> StageRun:
        """Persist or update a stage execution record."""
        self.session.add(stage_run)
        await self.session.commit()
        await self.session.refresh(stage_run)
        return stage_run

    async def get(self, stage_run_id: str) -> StageRun | None:
        """Fetch a stage run by unique identifier."""
        return await self.session.get(StageRun, stage_run_id)

    async def list_by_run(self, run_id: str) -> list[StageRun]:
        """Fetch all stage runs belonging to a pipeline run."""
        statement = select(StageRun).where(StageRun.run_id == run_id)
        result = await self.session.exec(statement)
        return list(result.all())

    async def get_by_stage(
        self, run_id: str, stage_id: str
    ) -> StageRun | None:
        """Fetch a specific stage execution record by run ID and stage ID."""
        statement = select(StageRun).where(
            StageRun.run_id == run_id, StageRun.stage_id == stage_id
        )
        result = await self.session.exec(statement)
        return result.first()

    async def update_status(
        self,
        stage_run_id: str,
        status: str,
        output: str | None = None,
        error: str | None = None,
        finished_at: datetime | None = None,
    ) -> StageRun | None:
        """Update stage status, error or output payload."""
        stage_run = await self.get(stage_run_id)
        if not stage_run:
            return None
        stage_run.status = status
        if output is not None:
            stage_run.output = output
        if error is not None:
            stage_run.error = error
        if finished_at is not None:
            stage_run.finished_at = finished_at
        self.session.add(stage_run)
        await self.session.commit()
        await self.session.refresh(stage_run)
        return stage_run


class AssetRepository:
    """Repository handling persisted asset metadata."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, asset: Asset) -> Asset:
        """Persist a new asset reference."""
        self.session.add(asset)
        await self.session.commit()
        await self.session.refresh(asset)
        return asset

    async def get(self, asset_id: str) -> Asset | None:
        """Fetch an asset by identifier."""
        return await self.session.get(Asset, asset_id)

    async def list_by_run(self, run_id: str) -> list[Asset]:
        """Fetch all assets produced during a run."""
        statement = select(Asset).where(Asset.run_id == run_id)
        result = await self.session.exec(statement)
        return list(result.all())
