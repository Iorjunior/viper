"""Speech-to-Text and Text-to-Speech stages using hardware backends."""

from pathlib import Path
from typing import Any

from viper.backends.resolver import get_stt, get_tts
from viper.backends.stt.base import Segment
from viper.config import VIPER_MEDIA_DIR
from viper.engine.assets import AudioAsset
from viper.engine.decorator import stage


@stage(
    name='transcribe',
    description='Transcribe spoken audio into timestamped text segments',
)
def transcribe(
    audio: str | Path,
    language: str | None = None,
) -> dict[str, Any]:
    """Transcribe audio file using resolved STT backend."""
    stt_backend = get_stt()
    transcription = stt_backend.transcribe(Path(audio), language=language)
    full_text = ' '.join(seg.text for seg in transcription.segments).strip()

    return {
        'transcription': transcription,
        'segments': transcription.segments,
        'text': full_text,
    }


@stage(
    name='synthesize',
    description='Synthesize speech audio from text using resolved TTS backend',
)
def synthesize(
    text: str,
    output_path: str | Path | None = None,
    voice: str = 'pf_dora',
) -> dict[str, Any]:
    """Generate audio speech from text string."""
    tts_backend = get_tts()
    dest = (
        Path(output_path)
        if output_path
        else VIPER_MEDIA_DIR / 'synthesized.wav'
    )
    dest.parent.mkdir(parents=True, exist_ok=True)

    tts_backend.synthesize(text, destination=dest, voice=voice)
    sample_rate = getattr(tts_backend, 'sample_rate', 24000)

    return {'audio': AudioAsset(path=dest, sample_rate=sample_rate)}


@stage(
    name='merge_segments',
    description='Merge neighboring speech segments within a max timing gap',
)
def merge_segments(
    segments: list[Segment],
    max_gap: float = 0.5,
) -> dict[str, Any]:
    """Combine adjacent speech segments when silence gap is within max_gap."""
    if not segments:
        return {'segments': []}

    merged: list[Segment] = []
    current = Segment(
        start=segments[0].start,
        end=segments[0].end,
        text=segments[0].text,
    )

    for nxt in segments[1:]:
        gap = nxt.start - current.end
        if gap <= max_gap:
            current.end = nxt.end
            current.text = f'{current.text} {nxt.text}'.strip()
        else:
            merged.append(current)
            current = Segment(start=nxt.start, end=nxt.end, text=nxt.text)

    merged.append(current)
    return {'segments': merged}
