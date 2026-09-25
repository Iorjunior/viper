"""Typed media assets for stage inputs and outputs."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BaseAsset:
    """Base class for all media and data assets."""

    path: Path = field(default_factory=Path)

    def __str__(self) -> str:
        return str(self.path)


@dataclass
class AudioAsset(BaseAsset):
    """Audio file asset with playback metadata."""

    duration: float | None = None
    sample_rate: int | None = None
    channels: int | None = None


@dataclass
class VideoAsset(BaseAsset):
    """Video file asset with visual and timing metadata."""

    duration: float | None = None
    resolution: str | None = None
    fps: float | None = None


@dataclass
class TextAsset(BaseAsset):
    """Plain text or subtitle asset with optional memory content."""

    content: str = ''


@dataclass
class ImageAsset(BaseAsset):
    """Image asset with resolution dimensions."""

    resolution: str | None = None
