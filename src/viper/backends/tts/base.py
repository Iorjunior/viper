"""Abstract base class for Text-to-Speech backends."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf


class TTSBackend(ABC):
    """Abstract interface for speech synthesis backends."""

    sample_rate: int = 24000

    @abstractmethod
    def synthesize_raw(self, text: str, **kwargs: Any) -> np.ndarray:
        """Synthesize text into raw PCM floating point audio samples."""

    def synthesize(self, text: str, destination: Path, **kwargs: Any) -> None:
        """Synthesize text and write directly to an audio file on disk."""
        audio = self.synthesize_raw(text, **kwargs)
        destination.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(destination), audio, self.sample_rate)
