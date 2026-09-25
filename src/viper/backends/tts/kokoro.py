"""Kokoro local TTS backend supporting PyTorch CPU and CUDA."""

import threading
from typing import Any, override

import numpy as np

from viper.backends.tts.base import TTSBackend

try:
    from kokoro import KPipeline
except ImportError:
    KPipeline = None  # type: ignore[assignment,misc]


class KokoroBackend(TTSBackend):
    """Local TTS engine powered by Kokoro-82M."""

    sample_rate: int = 24000
    _pipelines: dict[str, Any] = {}
    _lock = threading.Lock()

    def __init__(self, repo_id: str = 'hexgrad/Kokoro-82M') -> None:
        self.repo_id = repo_id

    def _get_pipeline(self, lang_code: str) -> Any:
        if KPipeline is None:
            msg = 'kokoro is not installed. Install with uv add kokoro'
            raise ImportError(msg)

        with self._lock:
            if lang_code not in self._pipelines:
                self._pipelines[lang_code] = KPipeline(
                    lang_code=lang_code, repo_id=self.repo_id
                )
            return self._pipelines[lang_code]

    @override
    def synthesize_raw(self, text: str, **kwargs: Any) -> np.ndarray:
        clean_text = ' '.join(str(text).split()).strip()
        if not clean_text:
            return np.zeros(0, dtype=np.float32)

        # 'p' for Portuguese, 'a' American English, etc.
        lang_code = kwargs.get('lang_code', 'p')
        voice = kwargs.get('voice', 'pf_dora')
        speed = float(kwargs.get('speed', 1.0))

        pipeline = self._get_pipeline(lang_code)

        chunks: list[np.ndarray] = []
        for _, _, audio in pipeline(clean_text, voice=voice, speed=speed):
            if audio is not None and len(audio) > 0:
                chunks.append(np.asarray(audio, dtype=np.float32))

        if not chunks:
            return np.zeros(0, dtype=np.float32)

        return np.concatenate(chunks)
