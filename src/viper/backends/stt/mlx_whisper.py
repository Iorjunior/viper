"""Apple Silicon MLX Whisper STT backend."""

from pathlib import Path
from typing import Any, cast, override

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
            'condition_on_previous_text': False,
        }
        if language is not None:
            options['language'] = language

        result_any: Any = mlx_whisper.transcribe(str(path), **options)
        result: dict[str, Any] = cast(dict[str, Any], result_any)

        raw_segments = cast(list[dict[str, Any]], result.get('segments', []))
        segments = [
            Segment(
                start=round(float(seg['start']), 3),
                end=round(float(seg['end']), 3),
                text=str(seg['text']).strip(),
            )
            for seg in raw_segments
        ]

        detected_lang = result.get('language')
        final_lang = (
            str(detected_lang) if detected_lang else (language or 'en')
        )

        return Transcription(
            language=final_lang,
            segments=segments,
        )
