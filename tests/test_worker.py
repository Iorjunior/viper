"""Unit and integration tests for the asynchronous worker module."""

import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import viper.worker.main as worker_main
import viper.worker.queue as queue_mod
import viper.worker.runner as runner_mod
from viper.db.models import Run
from viper.db.repositories import (
    AssetRepository,
    RunRepository,
    StageRunRepository,
)
from viper.db.session import async_session_maker
from viper.engine.assets import AudioAsset
from viper.engine.decorator import stage
from viper.engine.manifest_loader import register_manifest
from viper.engine.models import PipelineManifest, PipelineStageConfig
from viper.engine.registry import StageRegistry
from viper.server.ws import ConnectionManager
from viper.worker.queue import (
    clear_queue,
    dequeue,
    enqueue,
    enqueue_pending_from_db,
    is_queued,
    queue_size,
)
from viper.worker.runner import WorkerRunner, serialize_output


@pytest.fixture(autouse=True)
def clean_memory_queue() -> None:
    """Clear memory queue between test runs."""
    clear_queue()


@pytest.fixture
async def memory_db() -> AsyncGenerator[None, None]:
    """Setup in-memory SQLite database session isolated for tests."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    original_maker = async_session_maker
    mock_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    queue_mod.async_session_maker = mock_maker
    runner_mod.async_session_maker = mock_maker

    yield

    queue_mod.async_session_maker = original_maker
    runner_mod.async_session_maker = original_maker
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


def test_queue_operations() -> None:
    """Test memory queue enqueuing, deduplication, and dequeuing."""
    assert queue_size() == 0
    assert not is_queued('run_1')

    assert enqueue('run_1') is True
    assert queue_size() == 1
    assert is_queued('run_1')

    # Deduplication prevents duplicate queue entry
    assert enqueue('run_1') is False
    assert queue_size() == 1

    assert enqueue('run_2') is True
    assert queue_size() == 2


@pytest.mark.asyncio
async def test_dequeue_operation() -> None:
    """Test async dequeue popping items in FIFO order."""
    enqueue('run_a')
    enqueue('run_b')

    first = await dequeue()
    assert first == 'run_a'
    assert not is_queued('run_a')
    assert is_queued('run_b')

    second = await dequeue()
    assert second == 'run_b'
    assert queue_size() == 0


@pytest.mark.asyncio
async def test_enqueue_pending_from_db(memory_db: None) -> None:
    """Test polling unqueued pending runs from database."""
    async with queue_mod.async_session_maker() as session:
        repo = RunRepository(session)
        await repo.create(Run(pipeline_id='p1', status='pending'))
        await repo.create(Run(pipeline_id='p2', status='completed'))
        await repo.create(Run(pipeline_id='p3', status='pending'))

    count = await enqueue_pending_from_db()
    assert count == 2
    assert queue_size() == 2

    # Second poll does not re-enqueue already queued items
    count_again = await enqueue_pending_from_db()
    assert count_again == 0
    assert queue_size() == 2


def test_serialize_output_types() -> None:
    """Test recursive serialization of assets, paths, and collections."""
    asset = AudioAsset(path=Path('/tmp/test.wav'), duration=3.5)
    data = {
        'audio': asset,
        'path': Path('/tmp/video.mp4'),
        'nested': {'items': [1, Path('/tmp/file.txt')]},
    }
    serialized = serialize_output(data)
    assert serialized['audio']['path'] == '/tmp/test.wav'
    assert serialized['audio']['duration'] == 3.5
    assert serialized['path'] == '/tmp/video.mp4'
    assert serialized['nested']['items'][1] == '/tmp/file.txt'


@pytest.mark.asyncio
async def test_worker_runner_success(memory_db: None) -> None:
    """Test worker executing a pipeline to completion with DB updates."""
    custom_registry = StageRegistry()

    @stage(name='stage_add', registry=custom_registry)
    def add_step(x: int) -> dict[str, Any]:
        return {
            'value': x + 10,
            'audio': AudioAsset(path=Path('/tmp/out.wav'), duration=1.0),
        }

    manifest = PipelineManifest(
        id='worker_test_pipe',
        name='Worker Test Pipe',
        stages=[
            PipelineStageConfig(
                id='add_1',
                stage='stage_add',
                inputs={'x': '{{ inputs.x }}'},
            )
        ],
    )
    register_manifest(manifest)

    async with runner_mod.async_session_maker() as session:
        run_repo = RunRepository(session)
        run = await run_repo.create(
            Run(
                pipeline_id='worker_test_pipe',
                status='pending',
                inputs=json.dumps({'x': 5}),
            )
        )

    runner = WorkerRunner()
    runner.orchestrator.registry = custom_registry

    finished_run = await runner.execute_run(run.id)
    assert finished_run is not None
    assert finished_run.status == 'completed'
    assert finished_run.finished_at is not None

    outputs = json.loads(finished_run.outputs)
    assert outputs['add_1']['value'] == 15

    # Check stage runs in database
    async with runner_mod.async_session_maker() as session:
        stage_repo = StageRunRepository(session)
        stages = await stage_repo.list_by_run(run.id)
        assert len(stages) == 1
        assert stages[0].stage_id == 'add_1'
        assert stages[0].status == 'completed'
        assert stages[0].started_at is not None
        assert stages[0].finished_at is not None

        # Check asset persistence
        asset_repo = AssetRepository(session)
        assets = await asset_repo.list_by_run(run.id)
        assert len(assets) == 1
        assert assets[0].asset_type == 'AudioAsset'
        assert assets[0].path == '/tmp/out.wav'


@pytest.mark.asyncio
async def test_worker_runner_pipeline_not_found(memory_db: None) -> None:
    """Test worker marking run failed when pipeline manifest is missing."""
    async with runner_mod.async_session_maker() as session:
        run_repo = RunRepository(session)
        run = await run_repo.create(
            Run(pipeline_id='non_existent_pipeline', status='pending')
        )

    runner = WorkerRunner()
    result = await runner.execute_run(run.id)
    assert result is not None
    assert result.status == 'failed'
    assert result.finished_at is not None


@pytest.mark.asyncio
async def test_worker_runner_stage_failure(memory_db: None) -> None:
    """Test worker recording stage error and run failure in database."""
    custom_registry = StageRegistry()

    @stage(name='failing_worker_stage', registry=custom_registry)
    def broken_stage() -> None:
        raise RuntimeError('Stage crash simulation')

    manifest = PipelineManifest(
        id='failing_pipe',
        name='Failing Pipe',
        stages=[
            PipelineStageConfig(id='bad_step', stage='failing_worker_stage')
        ],
    )
    register_manifest(manifest)

    async with runner_mod.async_session_maker() as session:
        run_repo = RunRepository(session)
        run = await run_repo.create(
            Run(pipeline_id='failing_pipe', status='pending')
        )

    runner = WorkerRunner()
    runner.orchestrator.registry = custom_registry

    result = await runner.execute_run(run.id)
    assert result is not None
    assert result.status == 'failed'

    async with runner_mod.async_session_maker() as session:
        stage_repo = StageRunRepository(session)
        stages = await stage_repo.list_by_run(run.id)
        assert len(stages) == 1
        assert stages[0].status == 'failed'
        assert 'Stage crash simulation' in str(stages[0].error)


@pytest.mark.asyncio
async def test_worker_runner_broadcasts_websocket_events(
    memory_db: None,
) -> None:
    """Test worker progression broadcasts via WebSocket manager."""
    custom_registry = StageRegistry()

    @stage(name='quick_step', registry=custom_registry)
    def quick_fn() -> dict[str, str]:
        return {'status': 'done'}

    manifest = PipelineManifest(
        id='ws_test_pipe',
        name='WS Test Pipe',
        stages=[PipelineStageConfig(id='s1', stage='quick_step')],
    )
    register_manifest(manifest)

    events: list[dict[str, Any]] = []

    class MockConnectionManager(ConnectionManager):
        async def broadcast(
            self, run_id: str, message: dict[str, Any]
        ) -> None:
            events.append(message)

    mock_ws = MockConnectionManager()

    async with runner_mod.async_session_maker() as session:
        run_repo = RunRepository(session)
        run = await run_repo.create(
            Run(pipeline_id='ws_test_pipe', status='pending')
        )

    runner = WorkerRunner(ws=mock_ws)
    runner.orchestrator.registry = custom_registry

    await runner.execute_run(run.id)

    event_types = [e['event'] for e in events]
    assert 'run_started' in event_types
    assert 'stage_started' in event_types
    assert 'stage_completed' in event_types
    assert 'run_completed' in event_types


@pytest.mark.asyncio
async def test_worker_run_loop_and_stop(memory_db: None) -> None:
    """Test worker run_loop dequeuing jobs and stopping gracefully."""
    custom_registry = StageRegistry()

    @stage(name='noop_step', registry=custom_registry)
    def noop_fn() -> dict[str, str]:
        return {'ok': 'yes'}

    manifest = PipelineManifest(
        id='loop_pipe',
        name='Loop Pipe',
        stages=[PipelineStageConfig(id='step1', stage='noop_step')],
    )
    register_manifest(manifest)

    async with runner_mod.async_session_maker() as session:
        run_repo = RunRepository(session)
        run = await run_repo.create(
            Run(pipeline_id='loop_pipe', status='pending')
        )

    runner = WorkerRunner()
    runner.orchestrator.registry = custom_registry

    loop_task = asyncio.create_task(runner.run_loop(poll_interval=0.05))

    # Enqueue run
    enqueue(run.id)

    # Wait briefly for execution
    for _ in range(50):
        await asyncio.sleep(0.02)
        async with runner_mod.async_session_maker() as session:
            r = await RunRepository(session).get(run.id)
            if r and r.status == 'completed':
                break

    runner.stop()
    await loop_task

    async with runner_mod.async_session_maker() as session:
        final_run = await RunRepository(session).get(run.id)
        assert final_run is not None
        assert final_run.status == 'completed'


@pytest.mark.asyncio
async def test_worker_main_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test worker CLI main entrypoint initialization and execution."""
    init_called = False
    run_loop_called = False

    async def mock_init_db() -> None:
        nonlocal init_called
        init_called = True

    async def mock_run_loop(self: Any, poll_interval: float = 0.5) -> None:
        nonlocal run_loop_called
        run_loop_called = True

    monkeypatch.setattr(worker_main, 'init_db', mock_init_db)
    monkeypatch.setattr(WorkerRunner, 'run_loop', mock_run_loop)

    await worker_main.run_worker()
    assert init_called is True
    assert run_loop_called is True


def test_worker_main_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test worker CLI main synchronous wrapper invoking asyncio.run."""
    run_called = False

    def mock_run(coro: Any) -> None:
        nonlocal run_called
        run_called = True
        coro.close()

    monkeypatch.setattr(asyncio, 'run', mock_run)
    worker_main.main()
    assert run_called is True
