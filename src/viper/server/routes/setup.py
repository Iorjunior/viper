"""Setup and onboarding configuration API endpoints."""

import os
import platform
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from huggingface_hub import snapshot_download
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from viper.backends.resolver import detect_hardware
from viper.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    VIPER_LLM_BACKEND,
    VIPER_STT_BACKEND,
    VIPER_TTS_BACKEND,
    WHISPER_MODEL,
    get_config_value,
    set_runtime_setting,
)
from viper.db.repositories import SystemSettingRepository
from viper.db.session import get_session

setup_router = APIRouter(prefix='/api/setup', tags=['Setup'])

SUPPORTED_LOCAL_MODELS: list[dict[str, Any]] = [
    {
        'id': 'whisper-large-v3-turbo',
        'name': 'Whisper Large v3 Turbo',
        'capability': 'stt',
        'repo_id': (
            'mlx-community/whisper-large-v3-turbo'
            if platform.system() == 'Darwin' and platform.machine() == 'arm64'
            else 'Systran/faster-whisper-large-v3-turbo'
        ),
        'size_label': '~1.5 GB',
        'description': 'High-accuracy speech-to-text transcription.',
    },
    {
        'id': 'kokoro-82m',
        'name': 'Kokoro 82M',
        'capability': 'tts',
        'repo_id': 'hexgrad/Kokoro-82M',
        'size_label': '~82 MB',
        'description': 'Fast lightweight neural text-to-speech engine.',
    },
    {
        'id': 'htdemucs',
        'name': 'HTDemucs',
        'capability': 'audio_separation',
        'repo_id': 'adefossez/HTDemucs',
        'size_label': '~80 MB',
        'description': 'Music and vocal separation neural network.',
    },
    {
        'id': 'mlx-qwen-1.5b',
        'name': 'Qwen 2.5 1.5B Instruct (4-bit)',
        'capability': 'llm',
        'repo_id': 'mlx-community/Qwen2.5-1.5B-Instruct-4bit',
        'size_label': '~1.0 GB',
        'description': 'Metal-accelerated local translation LLM.',
        'apple_silicon_only': True,
    },
]


def _check_hf_cache(repo_id: str) -> bool:
    clean_id = repo_id.replace('/', '--')
    folder = f'models--{clean_id}'
    hf_cache = Path(
        os.getenv('HF_HOME', Path.home() / '.cache' / 'huggingface' / 'hub')
    )
    if (hf_cache / folder).exists():
        return True

    if 'demucs' in repo_id.lower():
        torch_hub = Path.home() / '.cache' / 'torch' / 'hub' / 'checkpoints'
        if any(torch_hub.glob('*demucs*')) if torch_hub.exists() else False:
            return True

    return False


class ValidateConnectionRequest(BaseModel):
    provider: str = 'openai'
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


class ValidateConnectionResponse(BaseModel):
    success: bool
    message: str
    models_available: list[str] = Field(default_factory=list)


class DownloadModelRequest(BaseModel):
    model_id: str


class CompleteSetupRequest(BaseModel):
    mode: str = 'local'
    stt_backend: str = 'auto'
    stt_model: str = 'large-v3-turbo'
    llm_backend: str = 'auto'
    tts_backend: str = 'kokoro'
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None


@setup_router.get('/status')
async def get_setup_status(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Retrieve setup progress, hardware capabilities, and models status."""
    repo = SystemSettingRepository(session)
    completed_raw = await repo.get('setup_completed')
    setup_completed = completed_raw == 'true'

    hardware = detect_hardware()

    model_status_list: list[dict[str, Any]] = []
    for item in SUPPORTED_LOCAL_MODELS:
        if item.get('apple_silicon_only') and not hardware.get(
            'is_apple_silicon'
        ):
            continue

        cached = _check_hf_cache(item['repo_id'])
        model_status_list.append({
            **item,
            'downloaded': cached,
        })

    current_config = {
        'stt_backend': get_config_value(
            'VIPER_STT_BACKEND', default=VIPER_STT_BACKEND
        ),
        'stt_model': get_config_value('WHISPER_MODEL', default=WHISPER_MODEL),
        'llm_backend': get_config_value(
            'VIPER_LLM_BACKEND', default=VIPER_LLM_BACKEND
        ),
        'tts_backend': get_config_value(
            'VIPER_TTS_BACKEND', default=VIPER_TTS_BACKEND
        ),
        'openai_base_url': get_config_value(
            'OPENAI_BASE_URL', default=OPENAI_BASE_URL
        ),
        'openai_model': get_config_value('OPENAI_MODEL', default=OPENAI_MODEL),
        'has_openai_key': bool(
            get_config_value('OPENAI_API_KEY', default=OPENAI_API_KEY)
        ),
    }

    return {
        'setup_completed': setup_completed,
        'hardware': hardware,
        'models': model_status_list,
        'current_config': current_config,
    }


async def _ping_endpoint(
    url: str, headers: dict[str, str]
) -> tuple[int, Any, str]:
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(url, headers=headers)
        try:
            body = resp.json()
        except Exception:
            body = None
        return resp.status_code, body, resp.text


@setup_router.post(
    '/validate-connection', response_model=ValidateConnectionResponse
)
async def validate_connection(
    req: ValidateConnectionRequest,
) -> ValidateConnectionResponse:
    """Validate external API or OpenAI-compatible endpoint connectivity."""
    base_url = (req.base_url or '').strip().rstrip('/')
    api_key = (req.api_key or '').strip()

    target_url = base_url if base_url else 'https://api.openai.com/v1'
    models_endpoint = f'{target_url}/models'

    headers: dict[str, str] = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    try:
        code, data, text = await _ping_endpoint(models_endpoint, headers)
    except Exception as exc:
        return ValidateConnectionResponse(
            success=False,
            message=f'Connection failed: {exc}',
        )

    if code == status.HTTP_200_OK:
        models: list[str] = []
        if isinstance(data, dict) and 'data' in data:
            models = [
                str(m.get('id', ''))
                for m in data['data']
                if isinstance(m, dict) and 'id' in m
            ]
        return ValidateConnectionResponse(
            success=True,
            message='Connection successful and endpoint verified.',
            models_available=models[:20],
        )

    if code == status.HTTP_401_UNAUTHORIZED:
        return ValidateConnectionResponse(
            success=False,
            message='Authentication failed. Please verify your API Key.',
        )

    return ValidateConnectionResponse(
        success=False,
        message=f'Endpoint returned HTTP {code}: {text[:100]}',
    )


@setup_router.post('/download-model')
async def download_model(req: DownloadModelRequest) -> dict[str, Any]:
    """Trigger background or inline download for a model repository."""
    matched = next(
        (m for m in SUPPORTED_LOCAL_MODELS if m['id'] == req.model_id), None
    )
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Model ID {req.model_id} not recognized.',
        )

    repo_id = matched['repo_id']
    try:
        snapshot_download(repo_id=repo_id)
        return {
            'success': True,
            'model_id': req.model_id,
            'message': f'Model {matched["name"]} downloaded successfully.',
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to download model {repo_id}: {exc}',
        ) from exc


@setup_router.post('/complete')
async def complete_setup(
    req: CompleteSetupRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Persist setup choices and mark onboarding as completed."""
    repo = SystemSettingRepository(session)

    settings_to_save: dict[str, str] = {
        'setup_completed': 'true',
        'VIPER_SETUP_MODE': req.mode,
        'VIPER_STT_BACKEND': req.stt_backend,
        'WHISPER_MODEL': req.stt_model,
        'VIPER_LLM_BACKEND': req.llm_backend,
        'VIPER_TTS_BACKEND': req.tts_backend,
    }

    if req.openai_base_url is not None:
        settings_to_save['OPENAI_BASE_URL'] = req.openai_base_url
    if req.openai_api_key is not None:
        settings_to_save['OPENAI_API_KEY'] = req.openai_api_key
    if req.openai_model is not None:
        settings_to_save['OPENAI_MODEL'] = req.openai_model

    await repo.set_many(settings_to_save)

    for k, v in settings_to_save.items():
        set_runtime_setting(k, v)

    return {
        'success': True,
        'message': 'Setup completed successfully.',
        'settings': settings_to_save,
    }
