import logging
from typing import Any

from viper.backends.resolver import get_llm
from viper.backends.stt.base import Segment
from viper.engine.decorator import stage

logger = logging.getLogger('viper.stages.text')


def _extract_raw_segments(transcript: Any) -> tuple[list[Any], list[str]]:
    if transcript is None:
        return [], []
    if isinstance(transcript, dict):
        segs = transcript.get('segments')
        if not segs and 'transcription' in transcript:
            trans = transcript['transcription']
            segs = getattr(trans, 'segments', None)
        if segs:
            return list(segs), []
        for key in ('text', 'texts', 'translated_texts'):
            val = transcript.get(key)
            if val:
                return [], [val] if isinstance(val, str) else list(val)
    elif isinstance(transcript, (list, tuple)):
        return list(transcript), []
    elif isinstance(transcript, str):
        return [], [transcript]
    return [], [str(transcript)]


def _segment_text(s: Any) -> str:
    if hasattr(s, 'text'):
        return str(s.text)
    if isinstance(s, dict):
        return str(s.get('text', ''))
    return str(s)


def _segment_duration(s: Any) -> float:
    if hasattr(s, 'start') and hasattr(s, 'end'):
        return float(s.end) - float(s.start)
    if isinstance(s, dict):
        return float(s.get('end', 0.0)) - float(s.get('start', 0.0))
    return 0.0


def _build_translated_segments(
    raw_segments: list[Any], translated: list[str]
) -> list[Segment]:
    if len(translated) != len(raw_segments):
        return []
    result: list[Segment] = []
    for orig, trans_text in zip(raw_segments, translated):
        start = (
            float(orig.start)
            if hasattr(orig, 'start')
            else float(orig.get('start', 0.0))
        )
        end = (
            float(orig.end)
            if hasattr(orig, 'end')
            else float(orig.get('end', 0.0))
        )
        result.append(
            Segment(start=start, end=end, text=str(trans_text).strip())
        )
    return result


@stage(
    name='translate',
    description='Translate speech segments to target language using LLM',
)
def translate(
    texts: list[str] | None = None,
    transcript: Any = None,
    target_language: str = 'pt-BR',
) -> dict[str, Any]:
    """Translate list of text chunks matching audio timing."""
    raw_segments: list[Any] = []
    if texts is None and transcript is not None:
        raw_segments, extracted_texts = _extract_raw_segments(transcript)
        if extracted_texts:
            texts = extracted_texts

    if raw_segments and texts is None:
        texts = [_segment_text(s) for s in raw_segments]

    target_texts = texts or []
    llm_backend = get_llm()
    durations = (
        [_segment_duration(s) for s in raw_segments] if raw_segments else None
    )

    logger.info(
        'Translating %d segments into %s using %s...',
        len(target_texts),
        target_language,
        llm_backend.__class__.__name__,
    )

    translated = (
        llm_backend.translate(
            target_texts,
            target_language=target_language,
            durations=durations,
        )
        if target_texts
        else []
    )
    full_text = ' '.join(translated).strip()
    translated_segments = _build_translated_segments(raw_segments, translated)
    logger.info(
        'Completed translation: %d segments built.', len(translated_segments)
    )

    return {
        'translated_texts': translated,
        'segments': translated_segments,
        'text': full_text,
        'translation': full_text,
    }
