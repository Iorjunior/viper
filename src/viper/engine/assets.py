import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BaseAsset(os.PathLike[str]):
    """Base class for all media and data assets."""

    path: Path = field(default_factory=Path)

    def __str__(self) -> str:
        return str(self.path)

    def __fspath__(self) -> str:
        return str(self.path)


def ensure_path(
    val: Any,
    preferred_keys: tuple[str, ...] = ('video', 'audio', 'file', 'path'),
) -> Path:
    """Extract a filesystem Path from a path, asset, or output dictionary."""
    if isinstance(val, dict):
        for key in preferred_keys:
            if key in val and val[key] is not None:
                return ensure_path(val[key], preferred_keys)
        if val:
            return ensure_path(next(iter(val.values())), preferred_keys)
        msg = 'Cannot extract path from an empty dictionary'
        raise ValueError(msg)
    if isinstance(val, BaseAsset):
        return val.path
    if isinstance(val, Path):
        return val
    return Path(str(val))


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
