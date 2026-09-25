"""OpenAI Whisper remote API STT backend."""

from pathlib import Path
from typing import Any, override

from viper.backends.stt.base import Segment, STTBackend, Transcription
from viper.config import OPENAI_API_KEY

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]


class OpenAISTTBackend(STTBackend):
    """STT implementation using OpenAI remote Whisper API."""

    def __init__(
        self, api_key: str | None = None, model: str = 'whisper-1'
    ) -> None:
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model

    @override
    def transcribe(
        self, path: Path, language: str | None = None
    ) -> Transcription:
        if OpenAI is None:
            msg = 'openai package not installed. Install with uv add openai'
            raise ImportError(msg)

        client = OpenAI(api_key=self.api_key)
        with path.open('rb') as audio_file:
            kwargs: dict[str, Any] = {
                'model': self.model,
                'response_format': 'verbose_json',
            }
            if language:
                kwargs['language'] = language

            response = client.audio.transcriptions.create(  # type: ignore[call-overload]
                file=audio_file, **kwargs
            )

        raw_segments = getattr(response, 'segments', []) or []
        segments = [
            Segment(
                start=round(float(seg.get('start', 0.0)), 3),
                end=round(float(seg.get('end', 0.0)), 3),
                text=seg.get('text', '').strip(),
            )
            for seg in raw_segments
        ]

        # Fallback if no verbose segments were returned
        if not segments and getattr(response, 'text', None):
            segments = [
                Segment(start=0.0, end=0.0, text=response.text.strip())
            ]

        return Transcription(
            language=getattr(response, 'language', language or 'en'),
            segments=segments,
        )
