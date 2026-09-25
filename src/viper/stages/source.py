"""Source input stages for importing or downloading media."""

from pathlib import Path
from typing import Any

from viper.config import VIPER_MEDIA_DIR
from viper.engine.assets import BaseAsset, VideoAsset
from viper.engine.decorator import stage

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


@stage(
    name='download_video',
    description='Download online video from URL using yt-dlp',
)
def download_video(
    url: str,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Download video stream from YouTube or web source."""
    if yt_dlp is None:
        msg = 'yt-dlp is not installed. Install with uv add yt-dlp'
        raise ImportError(msg)

    target_dir = Path(output_dir or VIPER_MEDIA_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    out_tmpl = str(target_dir / '%(id)s.%(ext)s')

    ydl_opts: dict[str, Any] = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': out_tmpl,
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        video_path = Path(filename)

    raw_duration = info.get('duration') if info else None
    duration = float(raw_duration) if raw_duration is not None else None
    resolution = None
    if info and 'width' in info and 'height' in info:
        resolution = f'{info["width"]}x{info["height"]}'

    return {
        'video': VideoAsset(
            path=video_path,
            duration=duration,
            resolution=resolution,
        )
    }


@stage(
    name='load_local_file',
    description='Load and validate a local file as a pipeline asset',
)
def load_local_file(path: str | Path) -> dict[str, Any]:
    """Validate existence of a local media file and return as an asset."""
    file_path = Path(path).resolve()
    if not file_path.is_file():
        msg = f'Specified file does not exist: {file_path}'
        raise FileNotFoundError(msg)

    return {'file': BaseAsset(path=file_path)}
