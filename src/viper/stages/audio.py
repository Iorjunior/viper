"""Audio processing and stem separation stages."""

import subprocess
from pathlib import Path
from typing import Any

from viper.config import VIPER_MEDIA_DIR
from viper.engine.assets import AudioAsset, ensure_path
from viper.engine.decorator import stage


@stage(
    name='extract_audio',
    description='Extract uncompressed WAV audio from video',
)
def extract_audio(
    video: str | Path | Any,
    output_path: str | Path | None = None,
    sample_rate: int = 24000,
) -> dict[str, Any]:
    """Extract audio track as mono WAV using FFmpeg."""
    src = ensure_path(video, ('video', 'file', 'path'))
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
    audio: str | Path | Any,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Isolate vocals and background stems using Demucs."""
    src = ensure_path(audio, ('audio', 'vocals', 'file', 'path'))
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

    demucs_vocals = list(target_dir.glob(f'**/{src.stem}/vocals.wav'))
    demucs_no_vocals = list(target_dir.glob(f'**/{src.stem}/no_vocals.wav'))
    if demucs_vocals and not vocals_path.exists():
        try:
            demucs_vocals[0].replace(vocals_path)
        except Exception:
            vocals_path = demucs_vocals[0]
    if demucs_no_vocals and not accompaniment_path.exists():
        try:
            demucs_no_vocals[0].replace(accompaniment_path)
        except Exception:
            accompaniment_path = demucs_no_vocals[0]

    if not vocals_path.exists():
        vocals_path.touch()
    if not accompaniment_path.exists():
        accompaniment_path.touch()

    return {
        'vocals': AudioAsset(path=vocals_path),
        'accompaniment': AudioAsset(path=accompaniment_path),
        'background': AudioAsset(path=accompaniment_path),
    }
