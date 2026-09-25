"""OpenAI remote API TTS backend."""

import io
from typing import Any, override

import numpy as np
import soundfile as sf

from viper.backends.tts.base import TTSBackend
from viper.config import OPENAI_API_KEY

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]


class OpenAITTSBackend(TTSBackend):
    """TTS implementation utilizing OpenAI audio speech API."""

    sample_rate: int = 24000

    def __init__(
        self,
        api_key: str | None = None,
        model: str = 'tts-1',
    ) -> None:
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model

    @override
    def synthesize_raw(self, text: str, **kwargs: Any) -> np.ndarray:
        if OpenAI is None:
            msg = 'openai package not installed. Install with uv add openai'
            raise ImportError(msg)

        client = OpenAI(api_key=self.api_key)
        voice = kwargs.get('voice', 'alloy')

        response = client.audio.speech.create(
            model=self.model,
            voice=voice,
            input=text,
            response_format='wav',
        )

        audio_bytes = response.content
        data, _ = sf.read(io.BytesIO(audio_bytes), dtype='float32')
        return np.asarray(data, dtype=np.float32)
