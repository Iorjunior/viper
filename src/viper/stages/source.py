"""Source input stages for importing or downloading media."""

from pathlib import Path
from typing import Any

from viper.config import VIPER_MEDIA_DIR
from viper.engine.assets import BaseAsset, VideoAsset, ensure_path
from viper.engine.decorator import stage

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


@stage(
    name='download_video',
    description='Download online video or load local file',
)
def download_video(
    source: str | None = None,
    url: str | None = None,
    output_dir: Path | str | None = None,
    max_resolution: int | str = 720,
) -> dict[str, Any]:
    """Download video stream or load local video file as asset."""
    raw_source = source or url
    if not raw_source:
        msg = "Missing required 'source' or 'url' parameter"
        raise ValueError(msg)

    if isinstance(raw_source, dict):
        raw_source = (
            raw_source.get('video')
            or raw_source.get('source')
            or raw_source.get('file')
            or raw_source.get('url')
            or raw_source
        )

    target_source = (
        str(raw_source.path)
        if isinstance(raw_source, BaseAsset)
        else str(raw_source)
    )

    # Check if target_source is an existing local file
    try:
        local_path = Path(target_source).resolve()
        if local_path.is_file():
            return {
                'video': VideoAsset(
                    path=local_path,
                    duration=None,
                    resolution=None,
                )
            }
    except Exception:
        pass

    if yt_dlp is None:
        msg = 'yt-dlp is not installed. Install with uv add yt-dlp'
        raise ImportError(msg)

    target_dir = Path(output_dir or VIPER_MEDIA_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    out_tmpl = str(target_dir / '%(id)s.%(ext)s')

    res_limit = (
        int(str(max_resolution).rstrip('pP'))
        if str(max_resolution).rstrip('pP').isdigit()
        else 720
    )
    format_selector = (
        f'bestvideo[height<={res_limit}][ext=mp4]+bestaudio[ext=m4a]/'
        f'bestvideo[height<={res_limit}]+bestaudio/'
        f'best[height<={res_limit}]/best'
    )

    ydl_opts: dict[str, Any] = {
        'format': format_selector,
        'outtmpl': out_tmpl,
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(target_source, download=True)
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
def load_local_file(path: str | Path | Any) -> dict[str, Any]:
    """Validate existence of a local media file and return as an asset."""
    file_path = ensure_path(path)
    if not file_path.is_file():
        msg = f'Specified file does not exist: {file_path}'
        raise FileNotFoundError(msg)

    return {'file': BaseAsset(path=file_path)}
