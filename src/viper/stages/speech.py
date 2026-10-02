import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from viper.backends.resolver import get_stt, get_tts
from viper.backends.stt.base import Segment
from viper.config import VIPER_MEDIA_DIR
from viper.engine.assets import AudioAsset, ensure_path
from viper.engine.decorator import stage

TERMINAL_PUNCTUATION = ('.', '?', '!', ';', ':', '…')
DEFAULT_MAX_SPEED = 1.50
DEFAULT_MIN_SPEED = 0.85
MIN_SPEED_DIFF = 0.02
FADE_DURATION_MS = 12.0
CHARS_PER_SECOND_PT = 14.5
MIN_AVAIL_DUR = 0.5
MIN_SLACK_LEAD_IN = 0.35
MAX_LEAD_IN = 0.15
LEAD_IN_RATIO = 0.30
SLOW_DOWN_RATIO = 0.70
SLOW_DOWN_MIN_GAP = 0.60
SLOW_DOWN_TARGET = 0.85
SPEED_UP_TOLERANCE = 1.01
INITIAL_FAST_RATIO = 1.05
INITIAL_SLOW_RATIO = 0.75


def apply_micro_fades(
    samples: np.ndarray, sample_rate: int, fade_ms: float = FADE_DURATION_MS
) -> np.ndarray:
    """Apply gentle linear fade-in and fade-out at chunk boundaries."""
    fade_len = int(sample_rate * (fade_ms / 1000.0))
    if len(samples) < fade_len * 2 or fade_len <= 0:
        return samples
    samples = samples.copy()
    fade_in = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
    fade_out = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
    samples[:fade_len] *= fade_in
    samples[-fade_len:] *= fade_out
    return samples


def filter_repeats(
    segments: list[Segment], max_consecutive: int = 2
) -> list[Segment]:
    """Filter out consecutive identical segments from hallucination."""
    filtered: list[Segment] = []
    prev_text = None
    count = 0
    for s in segments:
        clean = s.text.strip().lower().strip('.,!?;:…"\'')
        if not clean:
            continue
        if clean == prev_text:
            count += 1
            if count < max_consecutive:
                filtered.append(s)
        else:
            prev_text = clean
            count = 0
            filtered.append(s)
    return filtered


@stage(
    name='transcribe',
    description='Transcribe spoken audio into timestamped text segments',
)
def transcribe(
    audio: str | Path | Any,
    language: str | None = None,
) -> dict[str, Any]:
    """Transcribe audio file using resolved STT backend."""
    stt_backend = get_stt()
    src = ensure_path(audio, ('audio', 'vocals', 'file', 'path'))
    transcription = stt_backend.transcribe(src, language=language)
    clean_segments = filter_repeats(transcription.segments)
    transcription.segments = clean_segments
    full_text = ' '.join(seg.text for seg in clean_segments).strip()

    return {
        'transcription': transcription,
        'segments': clean_segments,
        'text': full_text,
    }


def _time_stretch_audio(
    samples: np.ndarray, speed_factor: float, sample_rate: int
) -> np.ndarray:
    """Time-stretch audio using FFmpeg pitch-preserving atempo filter."""
    if abs(speed_factor - 1.0) < MIN_SPEED_DIFF or len(samples) == 0:
        return samples

    factor = max(0.5, min(2.0, speed_factor))
    with (
        tempfile.NamedTemporaryFile(suffix='.wav') as in_f,
        tempfile.NamedTemporaryFile(suffix='.wav') as out_f,
    ):
        sf.write(in_f.name, samples, sample_rate)
        cmd = [
            'ffmpeg',
            '-y',
            '-i',
            in_f.name,
            '-filter:a',
            f'atempo={factor:.4f}',
            '-vn',
            out_f.name,
        ]
        res = subprocess.run(cmd, capture_output=True, check=False)
        if res.returncode == 0:
            out_samples, _ = sf.read(out_f.name, dtype='float32')
            if out_samples.ndim > 1:
                out_samples = out_samples.mean(axis=1)
            return out_samples
    return samples


def _synthesize_chunk(
    tts_backend: Any,
    text: str,
    voice: str,
    sample_rate: int,
    **kwargs: Any,
) -> np.ndarray:
    speed = float(kwargs.get('speed', 1.0))
    lang_code = str(kwargs.get('lang_code', 'p'))
    if hasattr(tts_backend, 'synthesize_raw'):
        try:
            raw = tts_backend.synthesize_raw(
                text, voice=voice, speed=speed, lang_code=lang_code
            )
            if isinstance(raw, np.ndarray) and len(raw) > 0:
                return raw
        except Exception:
            pass

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        tts_backend.synthesize(
            text,
            destination=tmp_path,
            voice=voice,
            speed=speed,
            lang_code=lang_code,
        )
        if tmp_path.exists() and tmp_path.stat().st_size > 0:
            data, _ = sf.read(str(tmp_path), dtype='float32')
            if data.ndim > 1:
                data = data.mean(axis=1)
            return data
    except Exception:
        pass
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
    return np.zeros(0, dtype=np.float32)


def _coerce_segment(s: Any) -> Segment | None:

    if isinstance(s, Segment):
        return s
    if isinstance(s, dict):
        return Segment(
            start=float(s.get('start', 0.0)),
            end=float(s.get('end', 0.0)),
            text=str(s.get('text', '')).strip(),
        )
    if hasattr(s, 'start') and hasattr(s, 'end') and hasattr(s, 'text'):
        return Segment(
            start=float(s.start),
            end=float(s.end),
            text=str(s.text).strip(),
        )
    return None


def _extract_segments(
    segments: Any = None, translation: Any = None
) -> list[Segment]:
    raw_list: list[Any] = []
    if segments:
        raw_list = list(segments)
    elif translation is not None:
        if isinstance(translation, dict):
            raw_list = translation.get('segments', [])
        elif isinstance(translation, (list, tuple)):
            raw_list = list(translation)

    result: list[Segment] = []
    for item in raw_list:
        coerced = _coerce_segment(item)
        if coerced and coerced.text.strip():
            result.append(coerced)
    return result


def _build_timeline_buffer(
    audio_chunks: list[tuple[np.ndarray, float, float]],
    sample_rate: int,
) -> np.ndarray:
    max_end = max(start + dur for _, start, dur in audio_chunks)
    total_samples = int(np.ceil((max_end + 0.5) * sample_rate))
    buffer = np.zeros(total_samples, dtype=np.float32)

    for chunk, start, _ in audio_chunks:
        start_sample = int(round(start * sample_rate))
        end_sample = start_sample + len(chunk)
        if end_sample > len(buffer):
            pad_size = end_sample - len(buffer) + sample_rate
            buffer = np.pad(buffer, (0, pad_size))
        buffer[start_sample:end_sample] += chunk

    peak = np.max(np.abs(buffer)) if len(buffer) > 0 else 0.0
    if peak > 1.0:
        buffer /= peak

    return buffer


def _extract_target_text(text: str | None, translation: Any) -> str:
    if text is not None:
        return text
    if translation is None:
        return ''
    if isinstance(translation, dict):
        raw = (
            translation.get('text')
            or translation.get('translation')
            or translation.get('translated_texts')
        )
        if isinstance(raw, (list, tuple)):
            return ' '.join(str(item) for item in raw)
        return str(raw or '')
    if isinstance(translation, (list, tuple)):
        return ' '.join(str(item) for item in translation)
    return str(translation)


def _predict_tts_speed(
    text: str, avail_dur: float, min_speed: float, max_speed: float
) -> float:
    char_count = len(text.strip())
    estimated_dur = (
        char_count / CHARS_PER_SECOND_PT if char_count > 0 else avail_dur
    )
    if estimated_dur > avail_dur * INITIAL_FAST_RATIO:
        return min(max_speed, max(1.0, estimated_dur / avail_dur))
    if estimated_dur < avail_dur * INITIAL_SLOW_RATIO:
        return max(min_speed, min(1.0, estimated_dur / avail_dur))
    return 1.0


def _adjust_chunk_timing(
    chunk: np.ndarray,
    avail_dur: float,
    sample_rate: int,
    min_speed: float,
    max_speed: float,
) -> np.ndarray:
    raw_dur = len(chunk) / float(sample_rate)
    if raw_dur > avail_dur * SPEED_UP_TOLERANCE:
        ratio = min(max_speed, raw_dur / avail_dur)
        chunk = _time_stretch_audio(chunk, ratio, sample_rate)
    elif (
        raw_dur < avail_dur * SLOW_DOWN_RATIO
        and avail_dur - raw_dur > SLOW_DOWN_MIN_GAP
    ):
        ratio = max(min_speed, raw_dur / (avail_dur * SLOW_DOWN_TARGET))
        chunk = _time_stretch_audio(chunk, ratio, sample_rate)
    return apply_micro_fades(chunk, sample_rate)


def _synthesize_placed_chunks(
    target_segments: list[Segment],
    tts_backend: Any,
    voice: str,
    sample_rate: int,
    **kwargs: Any,
) -> tuple[list[tuple[np.ndarray, float, float]], list[dict[str, Any]]]:
    max_speed = float(kwargs.get('max_speed', DEFAULT_MAX_SPEED))
    min_speed = float(kwargs.get('min_speed', DEFAULT_MIN_SPEED))
    lang_code = str(kwargs.get('lang_code', 'p'))
    placed: list[dict[str, Any]] = []
    chunks: list[tuple[np.ndarray, float, float]] = []
    prev_end = 0.0

    for idx, seg in enumerate(target_segments):
        start = max(float(seg.start), prev_end)
        if idx + 1 < len(target_segments):
            next_start = float(target_segments[idx + 1].start)
            avail_dur = max(next_start - start, MIN_AVAIL_DUR)
        else:
            avail_dur = max(float(seg.end) - start, MIN_AVAIL_DUR)

        initial_speed = _predict_tts_speed(
            seg.text, avail_dur, min_speed, max_speed
        )
        chunk = _synthesize_chunk(
            tts_backend,
            seg.text,
            voice,
            sample_rate,
            speed=round(initial_speed, 2),
            lang_code=lang_code,
        )
        if len(chunk) == 0:
            continue

        chunk = _adjust_chunk_timing(
            chunk, avail_dur, sample_rate, min_speed, max_speed
        )
        dur = len(chunk) / float(sample_rate)

        slack = avail_dur - dur
        if slack > MIN_SLACK_LEAD_IN:
            start += min(MAX_LEAD_IN, slack * LEAD_IN_RATIO)

        end = start + dur
        prev_end = end
        chunks.append((chunk, start, dur))
        placed.append({
            'id': str(idx),
            'start': round(start, 3),
            'end': round(end, 3),
            'duration': round(dur, 3),
            'text': seg.text,
        })
    return chunks, placed


@stage(
    name='synthesize',
    description='Synthesize speech audio from text using resolved TTS backend',
)
def synthesize(
    text: str | None = None,
    translation: Any = None,
    segments: list[Segment] | list[dict] | None = None,
    output_path: str | Path | None = None,
    voice: str = 'pf_dora',
    **kwargs: Any,
) -> dict[str, Any]:
    """Generate audio speech with timeline positioning for segments."""
    tts_backend = get_tts()
    sample_rate = getattr(tts_backend, 'sample_rate', 24000)
    dest = (
        Path(output_path)
        if output_path
        else VIPER_MEDIA_DIR / 'synthesized.wav'
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    max_speed = float(kwargs.get('max_speed', DEFAULT_MAX_SPEED))
    min_speed = float(kwargs.get('min_speed', DEFAULT_MIN_SPEED))
    lang_code = str(kwargs.get('lang_code', 'p'))

    target_segments = _extract_segments(segments, translation)
    if target_segments:
        chunks, placed = _synthesize_placed_chunks(
            target_segments,
            tts_backend,
            voice,
            sample_rate,
            max_speed=max_speed,
            min_speed=min_speed,
            lang_code=lang_code,
        )

        if chunks:
            buffer = _build_timeline_buffer(chunks, sample_rate)
            sf.write(str(dest), buffer, sample_rate)
            total_dur = len(buffer) / float(sample_rate)
            return {
                'audio': AudioAsset(
                    path=dest, sample_rate=sample_rate, duration=total_dur
                ),
                'segments': placed,
            }

    target_text = _extract_target_text(text, translation)
    tts_backend.synthesize(target_text, destination=dest, voice=voice)
    return {'audio': AudioAsset(path=dest, sample_rate=sample_rate)}


def _normalize_raw_segments(
    segments: list[Segment] | list[dict] | None = None,
    transcript: Any = None,
) -> list[Segment]:
    raw = segments
    if raw is None and transcript is not None:
        if isinstance(transcript, dict):
            raw = transcript.get('segments')
            if not raw and 'transcription' in transcript:
                raw = getattr(transcript['transcription'], 'segments', None)
        elif hasattr(transcript, 'segments'):
            raw = transcript.segments
        elif isinstance(transcript, list):
            raw = transcript

    norm_segments: list[Segment] = []
    if raw:
        for s in raw:
            c = _coerce_segment(s)
            if c:
                norm_segments.append(c)

    if not norm_segments:
        return []
    return filter_repeats(norm_segments)


@stage(
    name='merge_segments',
    description='Merge neighboring speech segments within a max timing gap',
)
def merge_segments(
    segments: list[Segment] | list[dict] | None = None,
    transcript: Any = None,
    max_gap: float = 0.5,
    max_duration: float = 10.0,
    max_characters: int = 200,
) -> dict[str, Any]:
    """Combine adjacent speech segments when silence gap is within max_gap."""
    norm_segments = _normalize_raw_segments(segments, transcript)
    if not norm_segments:
        return {'segments': [], 'text': ''}

    merged: list[Segment] = []
    current = Segment(
        start=norm_segments[0].start,
        end=norm_segments[0].end,
        text=norm_segments[0].text,
    )

    for nxt in norm_segments[1:]:
        term = current.text.rstrip().endswith(TERMINAL_PUNCTUATION)
        gap = nxt.start - current.end
        dur = nxt.end - current.start
        chars = len(current.text) + 1 + len(nxt.text)

        if (
            term
            or gap > max_gap
            or dur > max_duration
            or chars > max_characters
        ):
            merged.append(current)
            current = Segment(start=nxt.start, end=nxt.end, text=nxt.text)
        else:
            current.end = nxt.end
            current.text = f'{current.text} {nxt.text}'.strip()

    merged.append(current)
    return {
        'segments': merged,
        'text': ' '.join(seg.text for seg in merged).strip(),
    }
