"""Unit and integration tests for Model Context Protocol (MCP) server."""

from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import viper.server.mcp as mcp_mod
from viper.db.models import Run, StageRun
from viper.db.repositories import RunRepository, StageRunRepository
from viper.db.session import async_session_maker
from viper.server.app import app
from viper.server.mcp import (
    get_run_status,
    list_pipelines,
    list_stages,
    run_custom_pipeline,
    run_pipeline,
)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create FastAPI test client with lifespan triggered."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def memory_db() -> AsyncGenerator[None, None]:
    """Setup in-memory SQLite tables for test isolation."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Patch the session maker for MCP tools that create sessions directly
    original_maker = async_session_maker

    mock_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    mcp_mod.async_session_maker = mock_maker

    yield

    mcp_mod.async_session_maker = original_maker
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


async def test_mcp_list_pipelines() -> None:
    """Test MCP list_pipelines tool returns builtin pipelines."""
    pipelines = await list_pipelines()
    assert isinstance(pipelines, list)
    ids = [p['id'] for p in pipelines]
    assert 'download_video' in ids
    assert 'full_dubbing' in ids


async def test_mcp_list_stages() -> None:
    """Test MCP list_stages tool returns registered stages."""
    stages = await list_stages()
    assert isinstance(stages, list)
    names = [s['name'] for s in stages]
    assert 'transcribe' in names
    assert 'extract_audio' in names


async def test_mcp_run_pipeline(memory_db: None) -> None:
    """Test MCP run_pipeline tool creates a pending run."""
    result = await run_pipeline(
        pipeline_id='download_video',
        inputs={'source': 'https://youtube.com/watch?v=mcp_test'},
    )
    assert result['status'] == 'pending'
    assert result['pipeline_id'] == 'download_video'
    assert 'id' in result


async def test_mcp_run_pipeline_not_found(memory_db: None) -> None:
    """Test MCP run_pipeline tool with unknown ID returns error message."""
    result = await run_pipeline(
        pipeline_id='unknown_pipe',
        inputs={},
    )
    assert 'error' in result


async def test_mcp_run_custom_pipeline(memory_db: None) -> None:
    """Test MCP run_custom_pipeline tool creates ad-hoc run."""
    manifest = {
        'id': 'adhoc_pipe',
        'name': 'Ad-hoc Pipe',
        'stages': [
            {
                'id': 'download',
                'stage': 'download_video',
                'params': {'source': '{{ inputs.source }}'},
            }
        ],
    }
    result = await run_custom_pipeline(
        manifest=manifest,
        inputs={'source': 'test.mp4'},
    )
    assert result['status'] == 'pending'
    assert result['pipeline_id'] == 'adhoc_pipe'


async def test_mcp_get_run_status(memory_db: None) -> None:
    """Test MCP get_run_status tool fetches run and stages."""
    async with mcp_mod.async_session_maker() as session:
        run_repo = RunRepository(session)
        stage_repo = StageRunRepository(session)

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
                stage_id='download',
                status='completed',
                output='{"video": "/tmp/test.mp4"}',
            )
        )

    status_data = await get_run_status(run_id=run.id)
    assert status_data['id'] == run.id
    assert status_data['status'] == 'completed'
    assert len(status_data['stage_runs']) == 1

    missing = await get_run_status(run_id='unknown_id')
    assert 'error' in missing


def test_mcp_sse_mount(client: TestClient) -> None:
    """Test MCP SSE sub-application is mounted under /mcp/sse."""
    assert any(
        getattr(route, 'path', None) == '/mcp/sse' for route in app.routes
    )
    # Posting to message endpoint without session_id returns 400
    response = client.post('/mcp/sse/messages', json={})
    assert response.status_code == 400
    assert 'session_id is required' in response.text
