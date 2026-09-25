"""Unit and integration tests for database models and repositories."""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from viper.db.models import Asset, Run, StageRun
from viper.db.repositories import (
    AssetRepository,
    RunRepository,
    StageRunRepository,
)
from viper.db.session import ensure_sqlite_dir, get_session, init_db


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an in-memory SQLite AsyncSession for testing."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


def test_run_model_defaults() -> None:
    """Test Run model default values and fields."""
    run = Run(pipeline_id='full_dubbing')
    assert run.id is not None
    assert len(run.id) == 32
    assert run.pipeline_id == 'full_dubbing'
    assert run.status == 'pending'
    assert run.inputs == '{}'
    assert run.outputs == '{}'
    assert isinstance(run.created_at, datetime)
    assert run.finished_at is None


def test_stage_run_model_defaults() -> None:
    """Test StageRun model default values and fields."""
    stage_run = StageRun(run_id='run_123', stage_id='extract_audio')
    assert stage_run.id is not None
    assert len(stage_run.id) == 32
    assert stage_run.run_id == 'run_123'
    assert stage_run.stage_id == 'extract_audio'
    assert stage_run.status == 'pending'
    assert stage_run.output == '{}'
    assert stage_run.error is None
    assert stage_run.started_at is None
    assert stage_run.finished_at is None


def test_asset_model_defaults() -> None:
    """Test Asset model default values and fields."""
    asset = Asset(
        run_id='run_123',
        stage_id='extract_audio',
        asset_type='audio',
        path='/tmp/audio.wav',
    )
    assert asset.id is not None
    assert len(asset.id) == 32
    assert asset.run_id == 'run_123'
    assert asset.stage_id == 'extract_audio'
    assert asset.asset_type == 'audio'
    assert asset.path == '/tmp/audio.wav'
    assert asset.metadata_json == '{}'
    assert isinstance(asset.created_at, datetime)


def test_metadata_tables_registered() -> None:
    """Ensure SQLModel metadata contains all required tables."""
    table_names = set(SQLModel.metadata.tables.keys())
    assert 'run' in table_names
    assert 'stagerun' in table_names
    assert 'asset' in table_names


def test_ensure_sqlite_dir(tmp_path: Path) -> None:
    """Test directory creation helper for sqlite databases."""
    db_file = tmp_path / 'nested' / 'dir' / 'test.db'
    ensure_sqlite_dir(f'sqlite+aiosqlite:///{db_file}')
    assert db_file.parent.is_dir()

    # In-memory URLs should be no-op
    ensure_sqlite_dir('sqlite+aiosqlite:///:memory:')
    ensure_sqlite_dir('postgresql://user:pass@localhost/db')


async def test_init_db(tmp_path: Path) -> None:
    """Test init_db creates all tables on given engine."""
    db_file = tmp_path / 'init_test.db'
    test_engine = create_async_engine(f'sqlite+aiosqlite:///{db_file}')
    await init_db(test_engine)

    async with test_engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: SQLModel.metadata.tables.keys()
        )
        assert 'run' in tables
    await test_engine.dispose()


async def test_get_session_dependency() -> None:
    """Test get_session async generator yields an active AsyncSession."""
    session_gen = get_session()
    session = await anext(session_gen)
    try:
        assert isinstance(session, AsyncSession)
    finally:
        await session_gen.aclose()


async def test_run_repository_crud(db_session: AsyncSession) -> None:
    """Test RunRepository create, get, list, update_status, and delete."""
    repo = RunRepository(db_session)

    # 1. Create
    run = Run(
        pipeline_id='transcribe_translate',
        inputs='{"source": "test.mp4"}',
    )
    created = await repo.create(run)
    assert created.id == run.id

    # 2. Get
    fetched = await repo.get(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.pipeline_id == 'transcribe_translate'
    assert fetched.inputs == '{"source": "test.mp4"}'

    # 3. Non-existent get
    assert await repo.get('non-existent-id') is None

    # 4. List
    runs = await repo.list(limit=10, offset=0)
    assert len(runs) == 1
    assert runs[0].id == created.id

    # 5. Update status
    now = datetime.now(timezone.utc)
    updated = await repo.update_status(
        run_id=created.id,
        status='completed',
        outputs='{"transcript": "hello"}',
        finished_at=now,
    )
    assert updated is not None
    assert updated.status == 'completed'
    assert updated.outputs == '{"transcript": "hello"}'
    assert updated.finished_at is not None

    # 6. Update non-existent status
    assert (
        await repo.update_status(run_id='unknown', status='failed')
    ) is None

    # 7. Delete
    deleted = await repo.delete(created.id)
    assert deleted is True
    assert await repo.get(created.id) is None

    # 8. Delete non-existent
    assert await repo.delete('non-existent-id') is False


async def test_stage_run_repository_crud(db_session: AsyncSession) -> None:
    """Test StageRunRepository CRUD and update operations."""
    run_repo = RunRepository(db_session)
    stage_repo = StageRunRepository(db_session)

    run = await run_repo.create(Run(pipeline_id='test_pipe'))

    stage_run = StageRun(
        run_id=run.id,
        stage_id='download_video',
        status='running',
    )
    created = await stage_repo.create_or_update(stage_run)
    assert created.id == stage_run.id

    # Get
    fetched = await stage_repo.get(created.id)
    assert fetched is not None
    assert fetched.status == 'running'

    # Update status
    updated = await stage_repo.update_status(
        stage_run_id=created.id,
        status='completed',
        output='{"video": "/tmp/video.mp4"}',
    )
    assert updated is not None
    assert updated.status == 'completed'
    assert updated.output == '{"video": "/tmp/video.mp4"}'

    # Update status with error and finished_at
    failed_updated = await stage_repo.update_status(
        stage_run_id=created.id,
        status='failed',
        error='Something went wrong',
        finished_at=datetime.now(timezone.utc),
    )
    assert failed_updated is not None
    assert failed_updated.status == 'failed'
    assert failed_updated.error == 'Something went wrong'
    assert failed_updated.finished_at is not None

    # Update non-existent
    assert (
        await stage_repo.update_status(stage_run_id='unknown', status='failed')
    ) is None

    # List by run
    runs = await stage_repo.list_by_run(run.id)
    assert len(runs) == 1
    assert runs[0].id == created.id


async def test_asset_repository_crud(db_session: AsyncSession) -> None:
    """Test AssetRepository create, get, and list_by_run."""
    run_repo = RunRepository(db_session)
    asset_repo = AssetRepository(db_session)

    run = await run_repo.create(Run(pipeline_id='test_pipe'))

    asset = Asset(
        run_id=run.id,
        stage_id='audio_extract',
        asset_type='audio',
        path='/tmp/extracted.wav',
        metadata_json='{"sample_rate": 16000}',
    )
    created = await asset_repo.create(asset)
    assert created.id == asset.id

    fetched = await asset_repo.get(created.id)
    assert fetched is not None
    assert fetched.path == '/tmp/extracted.wav'

    # Non-existent asset
    assert await asset_repo.get('unknown-asset-id') is None

    assets = await asset_repo.list_by_run(run.id)
    assert len(assets) == 1
    assert assets[0].id == created.id


def test_alembic_migrations(tmp_path: Path) -> None:
    """Test executing alembic upgrade and downgrade on temporary database."""
    db_file = tmp_path / 'migration_test.db'
    cfg = Config('alembic.ini')
    cfg.set_main_option(
        'sqlalchemy.url', f'sqlite+aiosqlite:///{db_file.as_posix()}'
    )

    # Run upgrade to head
    command.upgrade(cfg, 'head')
    assert db_file.exists()

    # Run downgrade to base
    command.downgrade(cfg, 'base')
