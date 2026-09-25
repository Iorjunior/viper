"""Faster-Whisper STT backend for NVIDIA CUDA and CPU."""

from pathlib import Path
from typing import Any, override

from viper.backends.stt.base import Segment, STTBackend, Transcription

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None  # type: ignore[assignment,misc]


class FasterWhisperBackend(STTBackend):
    """STT implementation powered by faster-whisper (CTranslate2)."""

    def __init__(
        self,
        model_size: str = 'large-v3-turbo',
        device: str = 'cpu',
        compute_type: str | None = None,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type or (
            'float16' if device == 'cuda' else 'int8'
        )
        self._model: Any = None

    def _get_model(self) -> Any:
        if WhisperModel is None:
            msg = (
                'faster-whisper is not installed. '
                'Install with uv add faster-whisper'
            )
            raise ImportError(msg)

        if self._model is None:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    @override
    def transcribe(
        self, path: Path, language: str | None = None
    ) -> Transcription:
        model = self._get_model()
        segments_raw, info = model.transcribe(
            str(path),
            language=language,
            beam_size=5,
            word_timestamps=False,
        )

        segments = [
            Segment(
                start=round(float(seg.start), 3),
                end=round(float(seg.end), 3),
                text=seg.text.strip(),
            )
            for seg in segments_raw
        ]

        return Transcription(
            language=info.language or language or 'en',
            segments=segments,
        )
