"""Execution runner consuming pipeline runs and broadcasting stage updates."""

import asyncio
import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from viper.db.models import Asset, Run, StageRun
from viper.db.repositories import (
    AssetRepository,
    RunRepository,
    StageRunRepository,
)
from viper.db.session import async_session_maker
from viper.engine.assets import BaseAsset
from viper.engine.manifest_loader import get_manifest
from viper.engine.models import RunResult, RunStatus
from viper.engine.orchestrator import Orchestrator
from viper.server.ws import ConnectionManager, ws_manager
from viper.worker.queue import dequeue, enqueue_pending_from_db

logger = logging.getLogger('viper.worker.runner')


def serialize_output(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable structures."""
    if isinstance(obj, BaseAsset):
        data: dict[str, Any] = {
            'path': str(obj.path),
            'asset_type': obj.__class__.__name__,
        }
        if hasattr(obj, '__dict__'):
            for k, v in obj.__dict__.items():
                if k != 'path':
                    data[k] = serialize_output(v)
        return data

    if isinstance(obj, Path):
        return str(obj)

    if is_dataclass(obj) and not isinstance(obj, type):
        obj = asdict(obj)
    elif callable(getattr(obj, 'model_dump', None)):
        obj = getattr(obj, 'model_dump')()
    elif hasattr(obj, '__dict__') and not isinstance(obj, type):
        obj = {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}

    if isinstance(obj, dict):
        return {str(k): serialize_output(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [serialize_output(i) for i in obj]

    return obj


async def _persist_extracted_assets(
    asset_repo: AssetRepository,
    run_id: str,
    stage_id: str,
    output: Any,
) -> None:
    """Scan stage output for BaseAsset instances and persist to database."""
    assets_to_save: list[tuple[str, str, dict[str, Any]]] = []

    def _scan(val: Any) -> None:
        if isinstance(val, BaseAsset):
            meta = {
                k: str(v)
                for k, v in getattr(val, '__dict__', {}).items()
                if k != 'path' and v is not None
            }
            assets_to_save.append((
                val.__class__.__name__,
                str(val.path),
                meta,
            ))
        elif isinstance(val, dict):
            for v in val.values():
                _scan(v)
        elif isinstance(val, (list, tuple)):
            for v in val:
                _scan(v)

    _scan(output)
    for asset_type, path_str, meta in assets_to_save:
        await asset_repo.create(
            Asset(
                run_id=run_id,
                stage_id=stage_id,
                asset_type=asset_type,
                path=path_str,
                metadata_json=json.dumps(meta),
            )
        )


class WorkerRunner:
    """Consumes run jobs, executes DAG pipelines, and persists results."""

    def __init__(
        self,
        orchestrator: Orchestrator | None = None,
        ws: ConnectionManager | None = None,
    ) -> None:
        self.orchestrator = orchestrator or Orchestrator()
        self.ws = ws or ws_manager
        self._running = False

    async def _record_stage_start(self, run_id: str, stage_id: str) -> None:
        """Create or update stage execution record to running status."""
        logger.info("[Run %s] Stage '%s' started", run_id, stage_id)
        async with async_session_maker() as s:
            s_repo = StageRunRepository(s)
            existing = await s_repo.get_by_stage(run_id, stage_id)
            if not existing:
                sr = StageRun(
                    run_id=run_id,
                    stage_id=stage_id,
                    status='running',
                    started_at=datetime.now(timezone.utc),
                )
                await s_repo.create_or_update(sr)
            else:
                await s_repo.update_status(existing.id, status='running')
        await self.ws.broadcast(
            run_id,
            {'event': 'stage_started', 'run_id': run_id, 'stage_id': stage_id},
        )

    async def _record_stage_complete(
        self, run_id: str, stage_id: str, output: Any
    ) -> None:
        """Mark stage run completed, persist assets, and broadcast update."""
        logger.info(
            "[Run %s] Stage '%s' completed successfully", run_id, stage_id
        )
        serialized = serialize_output(output)
        output_json = json.dumps(serialized, default=str)
        async with async_session_maker() as s:
            s_repo = StageRunRepository(s)
            a_repo = AssetRepository(s)
            existing = await s_repo.get_by_stage(run_id, stage_id)
            if existing:
                await s_repo.update_status(
                    existing.id,
                    status='completed',
                    output=output_json,
                    finished_at=datetime.now(timezone.utc),
                )
            await _persist_extracted_assets(a_repo, run_id, stage_id, output)

        await self.ws.broadcast(
            run_id,
            {
                'event': 'stage_completed',
                'run_id': run_id,
                'stage_id': stage_id,
                'output': serialized,
            },
        )

    async def _record_stage_error(
        self, run_id: str, stage_id: str, exc: Exception
    ) -> None:
        """Mark stage run as failed and broadcast failure event."""
        logger.error(
            "[Run %s] Stage '%s' failed: %s",
            run_id,
            stage_id,
            exc,
            exc_info=True,
        )
        async with async_session_maker() as s:
            s_repo = StageRunRepository(s)
            existing = await s_repo.get_by_stage(run_id, stage_id)
            if existing:
                await s_repo.update_status(
                    existing.id,
                    status='failed',
                    error=str(exc),
                    finished_at=datetime.now(timezone.utc),
                )
        await self.ws.broadcast(
            run_id,
            {
                'event': 'stage_failed',
                'run_id': run_id,
                'stage_id': stage_id,
                'error': str(exc),
            },
        )

    async def _finalize_run(
        self, run_id: str, result: RunResult
    ) -> Run | None:
        """Update run table with final result and broadcast completion."""
        async with async_session_maker() as session:
            run_repo = RunRepository(session)
            if result.status == RunStatus.COMPLETED:
                logger.info('[Run %s] Pipeline run COMPLETED', run_id)
                serialized = serialize_output(result.stage_results)
                await run_repo.update_status(
                    run_id=run_id,
                    status='completed',
                    outputs=json.dumps(serialized, default=str),
                    finished_at=datetime.now(timezone.utc),
                )
                await self.ws.broadcast(
                    run_id,
                    {
                        'event': 'run_completed',
                        'run_id': run_id,
                        'outputs': serialized,
                    },
                )
            else:
                logger.error(
                    '[Run %s] Pipeline run FAILED: %s', run_id, result.error
                )
                await run_repo.update_status(
                    run_id=run_id,
                    status='failed',
                    finished_at=datetime.now(timezone.utc),
                )
                await self.ws.broadcast(
                    run_id,
                    {
                        'event': 'run_failed',
                        'run_id': run_id,
                        'error': result.error or 'Pipeline execution failed',
                    },
                )
            return await run_repo.get(run_id)

    async def execute_run(self, run_id: str) -> Run | None:
        """Execute a single pipeline run identified by run_id."""
        logger.info('[Run %s] Preparing execution', run_id)
        async with async_session_maker() as session:
            run_repo = RunRepository(session)
            run = await run_repo.get(run_id)
            if not run or run.status not in {'pending', 'running'}:
                logger.info(
                    '[Run %s] Skipping execution (current status: %s)',
                    run_id,
                    run.status if run else 'not found',
                )
                return run

            manifest = get_manifest(run.pipeline_id)
            if not manifest:
                logger.error(
                    "[Run %s] Pipeline '%s' not found", run_id, run.pipeline_id
                )
                await run_repo.update_status(
                    run_id=run_id,
                    status='failed',
                    finished_at=datetime.now(timezone.utc),
                )
                await self.ws.broadcast(
                    run_id,
                    {
                        'event': 'run_failed',
                        'run_id': run_id,
                        'error': f"Pipeline '{run.pipeline_id}' not found",
                    },
                )
                return await run_repo.get(run_id)

            await run_repo.update_status(run_id=run_id, status='running')
            await self.ws.broadcast(
                run_id,
                {
                    'event': 'run_started',
                    'run_id': run_id,
                    'pipeline_id': run.pipeline_id,
                },
            )

            try:
                inputs = json.loads(run.inputs) if run.inputs else {}
            except Exception:
                inputs = {}

        logger.info(
            "[Run %s] Executing pipeline '%s' with inputs: %s",
            run_id,
            run.pipeline_id,
            inputs,
        )

        result = await self.orchestrator.run(
            manifest,
            inputs,
            on_stage_start=lambda s: self._record_stage_start(run_id, s),
            on_stage_complete=lambda s, o: self._record_stage_complete(
                run_id, s, o
            ),
            on_stage_error=lambda s, e: self._record_stage_error(run_id, s, e),
        )

        return await self._finalize_run(run_id, result)

    @staticmethod
    async def _dequeue_next(timeout: float) -> str | None:
        """Attempt to pop next run ID from queue within timeout window."""
        try:
            return await asyncio.wait_for(dequeue(), timeout=timeout)
        except TimeoutError:
            return None

    async def run_loop(self, poll_interval: float = 0.5) -> None:
        """Run continuous worker loop polling queue and database."""
        self._running = True
        logger.info('Worker loop active (poll_interval=%.2fs)', poll_interval)
        while self._running:
            try:
                await enqueue_pending_from_db()
                run_id = await self._dequeue_next(poll_interval)
                if run_id:
                    await self.execute_run(run_id)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception(
                    'Unexpected exception in worker run_loop: %s', exc
                )
                await asyncio.sleep(poll_interval)

    def stop(self) -> None:
        """Signal the continuous runner loop to terminate."""
        logger.info('Stopping worker loop...')
        self._running = False
