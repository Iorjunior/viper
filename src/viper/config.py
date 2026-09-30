"""Application configuration managed via python-decouple."""

from pathlib import Path
from typing import Any

from decouple import config

# --- Backends -------------------------------------------------------------
VIPER_STT_BACKEND: str = str(config('VIPER_STT_BACKEND', default='auto'))
VIPER_LLM_BACKEND: str = str(config('VIPER_LLM_BACKEND', default='auto'))
VIPER_TTS_BACKEND: str = str(config('VIPER_TTS_BACKEND', default='kokoro'))

# --- Models & API ---------------------------------------------------------
WHISPER_MODEL: str = str(config('WHISPER_MODEL', default='large-v3-turbo'))
OPENAI_API_KEY: str = str(config('OPENAI_API_KEY', default=''))
_raw_ollama_host: str = str(config('OLLAMA_HOST', default=''))
_default_base_url: str = (
    f'{_raw_ollama_host.rstrip("/")}/v1' if _raw_ollama_host else ''
)
OPENAI_BASE_URL: str = str(
    config('OPENAI_BASE_URL', default=_default_base_url)
)
OPENAI_MODEL: str = str(
    config(
        'OPENAI_MODEL',
        default=str(config('OLLAMA_MODEL', default='gpt-4o-mini')),
    )
)
# Backward-compatibility aliases
OLLAMA_HOST: str = OPENAI_BASE_URL
OLLAMA_MODEL: str = OPENAI_MODEL

# --- Storage --------------------------------------------------------------
DATABASE_URL: str = str(
    config('DATABASE_URL', default='sqlite+aiosqlite:///data/viper.db')
)
VIPER_MEDIA_DIR: Path = Path(
    str(config('VIPER_MEDIA_DIR', default='data/media'))
)

# --- Server ---------------------------------------------------------------
HOST: str = str(config('HOST', default='0.0.0.0'))
PORT: int = config('PORT', default=8000, cast=int)
LOG_LEVEL: str = str(config('LOG_LEVEL', default='INFO'))


_RUNTIME_SETTINGS: dict[str, Any] = {}


def set_runtime_setting(key: str, value: Any) -> None:
    """Register or update a runtime configuration override."""
    _RUNTIME_SETTINGS[key] = value


def get_runtime_settings() -> dict[str, Any]:
    """Retrieve copy of all active runtime configuration overrides."""
    return dict(_RUNTIME_SETTINGS)


def get_config_value(key: str, default: Any = None) -> Any:
    """Retrieve configuration value checking runtime overrides first."""
    if key in _RUNTIME_SETTINGS and _RUNTIME_SETTINGS[key] is not None:
        return _RUNTIME_SETTINGS[key]
    return config(key, default=default)
