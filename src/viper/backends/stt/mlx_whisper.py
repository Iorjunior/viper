"""Apple Silicon MLX Whisper STT backend."""

from pathlib import Path
from typing import Any, override

from viper.backends.stt.base import Segment, STTBackend, Transcription

try:
    import mlx_whisper
except ImportError:
    mlx_whisper = None


class MlxWhisperBackend(STTBackend):
    """STT implementation optimized for Apple Silicon via MLX Whisper."""

    def __init__(
        self,
        model: str = 'mlx-community/whisper-large-v3-turbo',
    ) -> None:
        self.model = model

    @override
    def transcribe(
        self, path: Path, language: str | None = None
    ) -> Transcription:
        if mlx_whisper is None:
            msg = (
                'mlx-whisper is not installed. Install with '
                'uv sync --extra apple'
            )
            raise ImportError(msg)

        options: dict[str, Any] = {
            'path_or_hf_repo': self.model,
            'temperature': 0.0,
        }
        if language is not None:
            options['language'] = language

        result = mlx_whisper.transcribe(str(path), **options)

        raw_segments = result.get('segments', [])
        segments = [
            Segment(
                start=round(float(seg['start']), 3),
                end=round(float(seg['end']), 3),
                text=seg['text'].strip(),
            )
            for seg in raw_segments
        ]

        return Transcription(
            language=result.get('language') or language or 'en',
            segments=segments,
        )
