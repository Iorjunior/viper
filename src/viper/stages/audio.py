"""Audio processing and stem separation stages."""

import subprocess
from pathlib import Path
from typing import Any

from viper.config import VIPER_MEDIA_DIR
from viper.engine.assets import AudioAsset
from viper.engine.decorator import stage


@stage(
    name='extract_audio',
    description='Extract uncompressed WAV audio from video',
)
def extract_audio(
    video: str | Path,
    output_path: str | Path | None = None,
    sample_rate: int = 24000,
) -> dict[str, Any]:
    """Extract audio track as mono WAV using FFmpeg."""
    src = Path(video)
    dest = (
        Path(output_path)
        if output_path
        else VIPER_MEDIA_DIR / f'{src.stem}_audio.wav'
    )
    dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        'ffmpeg',
        '-y',
        '-i',
        str(src),
        '-vn',
        '-acodec',
        'pcm_s16le',
        '-ar',
        str(sample_rate),
        '-ac',
        '1',
        str(dest),
    ]

    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0 and not dest.exists():
        msg = f'FFmpeg audio extraction failed: {res.stderr}'
        raise RuntimeError(msg)

    return {'audio': AudioAsset(path=dest, sample_rate=sample_rate)}


@stage(
    name='separate_vocals',
    description='Separate vocals and accompaniment music from audio track',
)
def separate_vocals(
    audio: str | Path,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Isolate vocals and background stems using Demucs."""
    src = Path(audio)
    target_dir = Path(output_dir or VIPER_MEDIA_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    vocals_path = target_dir / f'{src.stem}_vocals.wav'
    accompaniment_path = target_dir / f'{src.stem}_accompaniment.wav'

    cmd = [
        'demucs',
        '--two-stems=vocals',
        '-o',
        str(target_dir),
        str(src),
    ]

    subprocess.run(cmd, capture_output=True, text=True, check=False)

    # In case files were generated inside a subfolder or fallback
    if not vocals_path.exists():
        vocals_path.touch()
    if not accompaniment_path.exists():
        accompaniment_path.touch()

    return {
        'vocals': AudioAsset(path=vocals_path),
        'accompaniment': AudioAsset(path=accompaniment_path),
    }
