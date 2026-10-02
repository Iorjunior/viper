import importlib.util
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


def _has_mlx_whisper() -> bool:
    if not _is_apple_silicon():
        return False
    return importlib.util.find_spec('mlx_whisper') is not None


def _has_mlx_lm() -> bool:
    if not _is_apple_silicon():
        return False
    return importlib.util.find_spec('mlx_lm') is not None


def detect_hardware() -> dict[str, Any]:
    """Detect system environment, accelerators and suggested profile."""
    is_mac_arm = _is_apple_silicon()
    cuda = _has_cuda()
    device = 'apple_silicon' if is_mac_arm else ('cuda' if cuda else 'cpu')
    recommended_mode = 'local' if (is_mac_arm or cuda) else 'cloud'
    return {
        'platform': platform.system(),
        'machine': platform.machine(),
        'device': device,
        'is_apple_silicon': is_mac_arm,
        'has_cuda': cuda,
        'recommended_mode': recommended_mode,
        'has_mlx': _has_mlx_whisper() and _has_mlx_lm(),
    }


def get_stt(**kwargs: Any) -> STTBackend:
    """Resolve and instantiate the configured or auto-detected STT backend."""
    backend = get_config_value('VIPER_STT_BACKEND', default='auto').lower()

    if backend == 'auto':
        if _is_apple_silicon() and _has_mlx_whisper():
            return MlxWhisperBackend(**kwargs)
        device = 'cuda' if _has_cuda() else 'cpu'
        return FasterWhisperBackend(device=device, **kwargs)

    if backend in {'faster_whisper', 'faster-whisper'}:
        device = 'cuda' if _has_cuda() else 'cpu'
        return FasterWhisperBackend(device=device, **kwargs)

    if backend in {'mlx_whisper', 'mlx-whisper', 'mlx'}:
        return MlxWhisperBackend(**kwargs)

    if backend == 'openai':
        api_key = kwargs.get(
            'api_key',
            get_config_value('OPENAI_API_KEY', default=OPENAI_API_KEY),
        )
        return OpenAISTTBackend(api_key=api_key or None, **kwargs)

    msg = f'Unsupported STT backend: {backend}'
    raise ValueError(msg)


def get_llm(**kwargs: Any) -> LLMBackend:
    """Resolve and instantiate the configured or auto-detected LLM backend."""
    backend = get_config_value('VIPER_LLM_BACKEND', default='auto').lower()
    base_url = get_config_value('OPENAI_BASE_URL', default=OPENAI_BASE_URL)
    model = get_config_value('OPENAI_MODEL', default=OPENAI_MODEL)
    api_key = get_config_value('OPENAI_API_KEY', default=OPENAI_API_KEY)

    if backend == 'auto':
        if _is_apple_silicon() and _has_mlx_lm():
            return MlxLmBackend(**kwargs)
        return OpenAICompatibleBackend(
            base_url=base_url or None,
            model=model,
            api_key=api_key or None,
            **kwargs,
        )

    if backend in {'mlx_lm', 'mlx-lm', 'mlx'}:
        return MlxLmBackend(**kwargs)

    if backend in {'openai', 'openai_compatible', 'compatible', 'ollama'}:
        return OpenAICompatibleBackend(
            base_url=base_url or None,
            model=model,
            api_key=api_key or None,
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
        api_key = kwargs.get(
            'api_key',
            get_config_value('OPENAI_API_KEY', default=OPENAI_API_KEY),
        )
        return OpenAITTSBackend(api_key=api_key or None, **kwargs)

    msg = f'Unsupported TTS backend: {backend}'
    raise ValueError(msg)
