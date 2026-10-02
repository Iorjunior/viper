"""Video rendering and muxing stages using FFmpeg."""

import subprocess
from pathlib import Path
from typing import Any

from viper.config import VIPER_MEDIA_DIR
from viper.engine.assets import VideoAsset, ensure_path
from viper.engine.decorator import stage


def _get_video_duration(path: Path) -> float | None:
    cmd = [
        'ffprobe',
        '-v',
        'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=noprint_wrappers=1:nokey=1',
        str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode == 0 and res.stdout.strip():
        try:
            return float(res.stdout.strip())
        except ValueError:
            return None
    return None


@stage(
    name='render_video',
    description='Mux video track with replaced or mixed audio track',
)
def render_video(
    video: str | Path | Any,
    audio: str | Path | Any | None = None,
    speech: str | Path | Any | None = None,
    background: str | Path | Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Replace original audio in video container with newly dubbed audio."""
    v_src = ensure_path(video, ('video', 'file', 'path'))
    audio_input = audio if audio is not None else speech
    if audio_input is None:
        msg = 'Either audio or speech must be provided to render_video'
        raise ValueError(msg)
    a_src = ensure_path(audio_input, ('audio', 'speech', 'file', 'path'))

    bg_src = None
    if background is not None:
        try:
            bg_cand = ensure_path(
                background,
                ('background', 'accompaniment', 'audio', 'file', 'path'),
            )
            if bg_cand.exists() and bg_cand.stat().st_size > 0:
                bg_src = bg_cand
        except Exception:
            bg_src = None

    dest = (
        Path(output_path)
        if output_path
        else VIPER_MEDIA_DIR / f'{v_src.stem}_dubbed.mp4'
    )
    dest.parent.mkdir(parents=True, exist_ok=True)

    v_dur = _get_video_duration(v_src)
    dur_args = ['-t', f'{v_dur:.3f}'] if v_dur is not None else []

    if bg_src is not None:
        cmd = [
            'ffmpeg',
            '-y',
            '-i',
            str(v_src),
            '-i',
            str(a_src),
            '-i',
            str(bg_src),
            '-filter_complex',
            '[1:a]asplit=2[speech_duck][speech_mix];'
            '[2:a][speech_duck]sidechaincompress=threshold=0.03:ratio=10:attack=20:release=250[ducked_bg];'
            '[speech_mix][ducked_bg]amix=inputs=2:duration=longest:dropout_transition=0[mixed]',
            '-c:v',
            'copy',
            '-c:a',
            'aac',
            '-map',
            '0:v:0',
            '-map',
            '[mixed]',
            '-movflags',
            '+faststart',
            *dur_args,
            str(dest),
        ]
    else:
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
            '-movflags',
            '+faststart',
            *dur_args,
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
    video: str | Path | Any,
    output_format: str = 'mp4',
    target_format: str | None = None,
    resolution: str | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Transcode video file to specified output format."""
    v_src = ensure_path(video, ('video', 'file', 'path'))
    effective_format = target_format or output_format
    dest = (
        Path(output_path)
        if output_path
        else VIPER_MEDIA_DIR / f'{v_src.stem}.{effective_format}'
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
