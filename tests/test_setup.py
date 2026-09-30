"""Unit and integration tests for setup wizard and repositories."""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from viper.config import get_config_value
from viper.db.repositories import SystemSettingRepository
from viper.db.session import get_session
from viper.server.app import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def override_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide isolated in-memory SQLite session override."""
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


@pytest.mark.asyncio
async def test_system_setting_repository(override_db: AsyncSession) -> None:
    """Test SystemSettingRepository CRUD operations."""
    repo = SystemSettingRepository(override_db)

    # Initial get
    val = await repo.get('non_existent')
    assert val is None

    # Set value
    setting = await repo.set('foo', 'bar')
    assert setting.key == 'foo'
    assert setting.value == 'bar'

    # Get updated value
    assert await repo.get('foo') == 'bar'

    # Update value
    await repo.set('foo', 'baz')
    assert await repo.get('foo') == 'baz'

    # Set many
    await repo.set_many({'k1': 'v1', 'k2': 'v2'})
    all_settings = await repo.get_all()
    assert all_settings['foo'] == 'baz'
    assert all_settings['k1'] == 'v1'
    assert all_settings['k2'] == 'v2'


def test_get_setup_status(
    client: TestClient, override_db: AsyncSession
) -> None:
    """Test setup status retrieval."""
    response = client.get('/api/setup/status')
    assert response.status_code == 200
    data = response.json()
    assert 'setup_completed' in data
    assert 'hardware' in data
    assert 'platform' in data['hardware']
    assert 'models' in data
    assert isinstance(data['models'], list)
    assert len(data['models']) > 0
    assert 'current_config' in data


def test_complete_setup(client: TestClient, override_db: AsyncSession) -> None:
    """Test completing setup configuration flow."""
    payload = {
        'mode': 'local',
        'stt_backend': 'faster_whisper',
        'stt_model': 'large-v3-turbo',
        'llm_backend': 'openai',
        'tts_backend': 'kokoro',
        'openai_base_url': 'http://localhost:11434/v1',
        'openai_api_key': 'test-secret-key',
        'openai_model': 'llama3.2',
    }

    response = client.post('/api/setup/complete', json=payload)
    assert response.status_code == 200
    assert response.json()['success'] is True

    # Verify status is now completed
    status_resp = client.get('/api/setup/status')
    assert status_resp.status_code == 200
    assert status_resp.json()['setup_completed'] is True

    # Verify runtime overrides
    assert get_config_value('VIPER_STT_BACKEND') == 'faster_whisper'
    assert get_config_value('OPENAI_API_KEY') == 'test-secret-key'
    assert get_config_value('OPENAI_BASE_URL') == 'http://localhost:11434/v1'


def test_validate_connection_success(client: TestClient) -> None:
    """Test successful connection validation."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'data': [{'id': 'gpt-4o'}, {'id': 'gpt-4o-mini'}]
    }

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        resp = client.post(
            '/api/setup/validate-connection',
            json={
                'provider': 'openai',
                'api_key': 'sk-test',
            },
        )
        assert resp.status_code == 200
        res = resp.json()
        assert res['success'] is True
        assert 'gpt-4o' in res['models_available']


def test_validate_connection_auth_failure(client: TestClient) -> None:
    """Test authentication failure during connection validation."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = 'Unauthorized'

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        resp = client.post(
            '/api/setup/validate-connection',
            json={
                'provider': 'openai',
                'api_key': 'invalid-key',
            },
        )
        assert resp.status_code == 200
        res = resp.json()
        assert res['success'] is False
        assert 'Authentication failed' in res['message']


def test_download_model_endpoint(client: TestClient) -> None:
    """Test model download triggering."""
    with patch(
        'viper.server.routes.setup.snapshot_download'
    ) as mock_download:
        mock_download.return_value = '/fake/cache/path'

        resp = client.post(
            '/api/setup/download-model',
            json={'model_id': 'kokoro-82m'},
        )
        assert resp.status_code == 200
        assert resp.json()['success'] is True
        mock_download.assert_called_once()


def test_download_unknown_model(client: TestClient) -> None:
    """Test downloading nonexistent model ID."""
    resp = client.post(
        '/api/setup/download-model',
        json={'model_id': 'unknown-fake-model'},
    )
    assert resp.status_code == 404
