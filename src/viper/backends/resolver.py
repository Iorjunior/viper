"""Hardware detection and backend instance resolver."""

import platform
from typing import Any

import torch

from viper.backends.llm.base import LLMBackend
from viper.backends.llm.mlx_lm import MlxLmBackend
from viper.backends.llm.openai_compatible import OpenAICompatibleBackend
from viper.backends.stt.base import STTBackend
from viper.backends.stt.faster_whisper import FasterWhisperBackend
from viper.backends.stt.mlx_whisper import MlxWhisperBackend
from viper.backends.stt.openai import OpenAISTTBackend
from viper.backends.tts.base import TTSBackend
from viper.backends.tts.kokoro import KokoroBackend
from viper.backends.tts.openai import OpenAITTSBackend
from viper.config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    get_config_value,
)


def _is_apple_silicon() -> bool:
    return platform.system() == 'Darwin' and platform.machine() == 'arm64'


def _has_cuda() -> bool:
    try:
        return torch.cuda.is_available()
    except Exception:
        return False


def get_stt(**kwargs: Any) -> STTBackend:
    """Resolve and instantiate the configured or auto-detected STT backend."""
    backend = get_config_value('VIPER_STT_BACKEND', default='auto').lower()

    if backend == 'auto':
        if _is_apple_silicon():
            return MlxWhisperBackend(**kwargs)
        device = 'cuda' if _has_cuda() else 'cpu'
        return FasterWhisperBackend(device=device, **kwargs)

    if backend in {'faster_whisper', 'faster-whisper'}:
        device = 'cuda' if _has_cuda() else 'cpu'
        return FasterWhisperBackend(device=device, **kwargs)

    if backend in {'mlx_whisper', 'mlx-whisper', 'mlx'}:
        return MlxWhisperBackend(**kwargs)

    if backend == 'openai':
        return OpenAISTTBackend(**kwargs)

    msg = f'Unsupported STT backend: {backend}'
    raise ValueError(msg)


def get_llm(**kwargs: Any) -> LLMBackend:
    """Resolve and instantiate the configured or auto-detected LLM backend."""
    backend = get_config_value('VIPER_LLM_BACKEND', default='auto').lower()

    if backend == 'auto':
        if _is_apple_silicon():
            return MlxLmBackend(**kwargs)
        return OpenAICompatibleBackend(
            base_url=f'{OLLAMA_HOST.rstrip("/")}/v1',
            model=OLLAMA_MODEL,
            api_key='ollama',
            **kwargs,
        )

    if backend == 'ollama':
        return OpenAICompatibleBackend(
            base_url=f'{OLLAMA_HOST.rstrip("/")}/v1',
            model=OLLAMA_MODEL,
            api_key='ollama',
            **kwargs,
        )

    if backend in {'mlx_lm', 'mlx-lm', 'mlx'}:
        return MlxLmBackend(**kwargs)

    if backend in {'openai', 'openai_compatible', 'compatible'}:
        return OpenAICompatibleBackend(
            base_url=OPENAI_BASE_URL or None,
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            **kwargs,
        )

    msg = f'Unsupported LLM backend: {backend}'
    raise ValueError(msg)


def get_tts(**kwargs: Any) -> TTSBackend:
    """Resolve and instantiate the configured or auto-detected TTS backend."""
    backend = get_config_value('VIPER_TTS_BACKEND', default='kokoro').lower()

    if backend in {'auto', 'kokoro'}:
        return KokoroBackend(**kwargs)

    if backend == 'openai':
        return OpenAITTSBackend(**kwargs)

    msg = f'Unsupported TTS backend: {backend}'
    raise ValueError(msg)
