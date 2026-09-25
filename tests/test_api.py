"""Unit and integration tests for FastAPI REST API endpoints."""

from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from viper.db.models import Run, StageRun
from viper.db.repositories import RunRepository, StageRunRepository
from viper.db.session import get_session
from viper.main import serve
from viper.server.app import app
from viper.server.routes.assets import stream_asset
from viper.server.ws import ws_manager


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create FastAPI test client with lifespan triggered."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def override_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide in-memory SQLite session override."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:

        async def _override_get_session() -> AsyncGenerator[
            AsyncSession, None
        ]:
            yield session

        app.dependency_overrides[get_session] = _override_get_session
        yield session
        app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert 'version' in data


def test_list_pipelines(client: TestClient) -> None:
    """Test listing all available pipeline manifests."""
    response = client.get('/api/pipelines')
    assert response.status_code == 200
    pipelines = response.json()
    assert isinstance(pipelines, list)
    pipeline_ids = [p['id'] for p in pipelines]
    assert 'full_dubbing' in pipeline_ids
    assert 'download_video' in pipeline_ids


def test_get_pipeline_details(client: TestClient) -> None:
    """Test retrieving pipeline details by ID."""
    response = client.get('/api/pipelines/download_video')
    assert response.status_code == 200
    data = response.json()
    assert data['id'] == 'download_video'
    assert data['name'] == 'Download Video'
    assert 'stages' in data


def test_get_pipeline_not_found(client: TestClient) -> None:
    """Test retrieving a non-existent pipeline returns 404."""
    response = client.get('/api/pipelines/non_existent_pipeline')
    assert response.status_code == 404


def test_list_stages(client: TestClient) -> None:
    """Test listing registered engine processing stages."""
    response = client.get('/api/stages')
    assert response.status_code == 200
    stages = response.json()
    assert isinstance(stages, list)
    stage_names = [s['name'] for s in stages]
    assert 'transcribe' in stage_names
    assert 'extract_audio' in stage_names


async def test_list_runs_empty(
    client: TestClient, override_db: AsyncSession
) -> None:
    """Test listing runs when database has no records."""
    response = client.get('/api/runs')
    assert response.status_code == 200
    assert response.json() == []


async def test_get_run_details(
    client: TestClient,
    override_db: AsyncSession,
) -> None:
    """Test retrieving run details including associated stage runs."""
    run_repo = RunRepository(override_db)
    stage_repo = StageRunRepository(override_db)

    run = await run_repo.create(
        Run(
            pipeline_id='download_video',
            inputs='{"source": "test.mp4"}',
            status='completed',
        )
    )
    await stage_repo.create_or_update(
        StageRun(
            run_id=run.id,
            stage_id='source',
            status='completed',
            output='{"video": "/tmp/test.mp4"}',
        )
    )

    # List runs with pagination
    list_resp = client.get('/api/runs?limit=10&offset=0')
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert len(runs) == 1
    assert runs[0]['id'] == run.id

    # Get run by ID
    get_resp = client.get(f'/api/runs/{run.id}')
    assert get_resp.status_code == 200
    run_data = get_resp.json()
    assert run_data['id'] == run.id
    assert run_data['status'] == 'completed'
    assert len(run_data['stage_runs']) == 1
    assert run_data['stage_runs'][0]['stage_id'] == 'source'


async def test_get_run_not_found(
    client: TestClient, override_db: AsyncSession
) -> None:
    """Test retrieving non-existent run returns 404."""
    response = client.get('/api/runs/non-existent-uuid')
    assert response.status_code == 404


def test_main_serve() -> None:
    """Test CLI serve runner invokes uvicorn."""
    with patch('uvicorn.run') as mock_run:
        serve()
        assert mock_run.called


async def test_run_pipeline_success(
    client: TestClient, override_db: AsyncSession
) -> None:
    """Test triggering a pipeline execution creates a pending run."""
    payload = {'source': 'https://youtube.com/watch?v=test'}
    response = client.post('/api/pipelines/download_video/run', json=payload)
    assert response.status_code == 201
    run_data = response.json()
    assert run_data['pipeline_id'] == 'download_video'
    assert run_data['status'] == 'pending'
    assert 'id' in run_data


async def test_run_pipeline_not_found(
    client: TestClient, override_db: AsyncSession
) -> None:
    """Test triggering a non-existent pipeline returns 404."""
    response = client.post(
        '/api/pipelines/unknown_pipeline/run',
        json={},
    )
    assert response.status_code == 404


async def test_asset_streaming(client: TestClient, tmp_path: Path) -> None:
    """Test streaming an asset file and path traversal prevention."""
    media_dir = tmp_path / 'media'
    media_dir.mkdir(parents=True, exist_ok=True)
    sample_file = media_dir / 'test.txt'
    sample_file.write_text('sample media content', encoding='utf-8')

    with patch('viper.server.routes.assets.VIPER_MEDIA_DIR', media_dir):
        # 1. Existing file
        resp = client.get('/api/assets/test.txt')
        assert resp.status_code == 200
        assert resp.text == 'sample media content'

        # 2. Missing file
        missing_resp = client.get('/api/assets/missing.txt')
        assert missing_resp.status_code == 404

        # 3. Path traversal attack
        with pytest.raises(HTTPException) as exc_info:
            await stream_asset('../secret.txt')
        assert exc_info.value.status_code == 403


async def test_websocket_broadcast(client: TestClient) -> None:
    """Test WebSocket connection and message broadcasting."""
    with client.websocket_connect('/ws/run_abc123') as websocket:
        await ws_manager.broadcast(
            run_id='run_abc123',
            message={'event': 'stage_progress', 'percent': 50},
        )
        data = websocket.receive_json()
        assert data['event'] == 'stage_progress'
        assert data['percent'] == 50
