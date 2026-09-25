"""Application configuration managed via python-decouple."""

from pathlib import Path
from typing import Any

from decouple import config

# --- Backends -------------------------------------------------------------
VIPER_STT_BACKEND: str = str(config('VIPER_STT_BACKEND', default='auto'))
VIPER_LLM_BACKEND: str = str(config('VIPER_LLM_BACKEND', default='auto'))
VIPER_TTS_BACKEND: str = str(config('VIPER_TTS_BACKEND', default='kokoro'))

# --- Models ---------------------------------------------------------------
WHISPER_MODEL: str = str(config('WHISPER_MODEL', default='large-v3-turbo'))
OLLAMA_HOST: str = str(config('OLLAMA_HOST', default='http://localhost:11434'))
OLLAMA_MODEL: str = str(config('OLLAMA_MODEL', default='qwen2.5:1.5b'))
OPENAI_API_KEY: str = str(config('OPENAI_API_KEY', default=''))
OPENAI_BASE_URL: str = str(config('OPENAI_BASE_URL', default=''))
OPENAI_MODEL: str = str(config('OPENAI_MODEL', default='gpt-4o-mini'))

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


def get_config_value(key: str, default: Any = None) -> Any:
    """Helper to retrieve configuration value, allowing test patches."""
    return config(key, default=default)
