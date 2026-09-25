"""Abstract base class and data models for Speech-to-Text backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Segment:
    """Represents a transcribed speech segment with timing."""

    start: float
    end: float
    text: str


@dataclass
class Transcription:
    """Complete transcription result containing language and segments."""

    language: str
    segments: list[Segment]


class STTBackend(ABC):
    """Abstract interface for Speech-to-Text backends."""

    @abstractmethod
    def transcribe(
        self, path: Path, language: str | None = None
    ) -> Transcription:
        """Transcribe audio from file into structured transcription."""
