"""Video rendering and muxing stages using FFmpeg."""

import subprocess
from pathlib import Path
from typing import Any

from viper.config import VIPER_MEDIA_DIR
from viper.engine.assets import VideoAsset
from viper.engine.decorator import stage


@stage(
    name='render_video',
    description='Mux video track with replaced or mixed audio track',
)
def render_video(
    video: str | Path,
    audio: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Replace original audio in video container with newly dubbed audio."""
    v_src = Path(video)
    a_src = Path(audio)
    dest = (
        Path(output_path)
        if output_path
        else VIPER_MEDIA_DIR / f'{v_src.stem}_dubbed.mp4'
    )
    dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        'ffmpeg',
        '-y',
        '-i',
        str(v_src),
        '-i',
        str(a_src),
        '-c:v',
        'copy',
        '-c:a',
        'aac',
        '-map',
        '0:v:0',
        '-map',
        '1:a:0',
        '-shortest',
        str(dest),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0 and not dest.exists():
        msg = f'Video rendering failed: {res.stderr}'
        raise RuntimeError(msg)

    return {'video': VideoAsset(path=dest)}


@stage(
    name='convert_video',
    description='Transcode video file into target container format',
)
def convert_video(
    video: str | Path,
    output_format: str = 'mp4',
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Transcode video file to specified output format."""
    v_src = Path(video)
    dest = (
        Path(output_path)
        if output_path
        else VIPER_MEDIA_DIR / f'{v_src.stem}.{output_format}'
    )
    dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        'ffmpeg',
        '-y',
        '-i',
        str(v_src),
        '-c:v',
        'libx264',
        '-c:a',
        'aac',
        str(dest),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0 and not dest.exists():
        msg = f'Video conversion failed: {res.stderr}'
        raise RuntimeError(msg)

    return {'video': VideoAsset(path=dest)}
