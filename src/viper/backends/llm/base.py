"""Abstract base class for Large Language Model backends."""

import json
import logging
import re
from abc import ABC, abstractmethod

logger = logging.getLogger('viper.backends.llm')

LANGUAGE_NAMES: dict[str, str] = {
    'pt-br': 'Portuguese (Brazil)',
    'pt': 'Portuguese',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'ru': 'Russian',
}


def _format_language_name(code: str) -> str:
    cleaned = str(code).strip().lower().replace('_', '-')
    return LANGUAGE_NAMES.get(cleaned, str(code))


def _parse_numbered_lines(raw_output: str, count: int) -> list[str | None]:
    line_results: list[str | None] = [None] * count
    for raw_line in raw_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(
            r'^(?:\[|\{|\"|\')?(\d+)(?:\[.*?\])?[\:\.\-\)]\s*[\"\']?(.*?)[\"\']?$',
            line,
        )
        if match:
            idx = int(match.group(1))
            text = match.group(2).strip()
            if 0 <= idx < count and line_results[idx] is None and text:
                line_results[idx] = text
    return line_results


def _parse_json_list(raw_output: str, count: int) -> list[str] | None:
    match = re.search(r'\[.*\]', raw_output, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, list) and len(parsed) == count:
            return [str(s).strip() for s in parsed]
    except json.JSONDecodeError:
        pass
    return None


class LLMBackend(ABC):
    """Abstract interface for LLM backends (translation and generation)."""

    @abstractmethod
    def generate(self, prompt: str, system: str = '') -> str:
        """Generate text response given a prompt and optional instructions."""

    def translate(
        self,
        segments: list[str],
        target_language: str,
        durations: list[float] | None = None,
    ) -> list[str]:
        """Translate a list of text segments to target language in batches."""
        if not segments:
            return []

        batch_size = 6
        total_batches = (len(segments) + batch_size - 1) // batch_size
        logger.info(
            'Translating %d segments into %s across %d batches...',
            len(segments),
            target_language,
            total_batches,
        )
        results: list[str] = []
        for i in range(0, len(segments), batch_size):
            batch_num = (i // batch_size) + 1
            chunk = segments[i : i + batch_size]
            logger.info(
                'Translating batch %d/%d (%d segments)...',
                batch_num,
                total_batches,
                len(chunk),
            )
            chunk_durations = (
                durations[i : i + batch_size]
                if durations is not None
                else None
            )
            chunk_results = self._translate_batch(
                chunk, target_language, chunk_durations
            )
            results.extend(chunk_results)

        logger.info('Translated all %d segments successfully.', len(results))
        return results

    def _translate_single(
        self,
        text: str,
        target_language: str,
        duration: float | None = None,
    ) -> list[str]:
        target_name = _format_language_name(target_language)
        dur_instruction_pt = (
            f'\nA fala dublada deve durar cerca de {duration:.1f} segundos. '
            'Adapte concisamente para dublagem.'
            if duration
            else ''
        )
        dur_instruction_en = (
            f'\nThe dubbed speech should fit about {duration:.1f} seconds. '
            'Be concise and natural.'
            if duration
            else ''
        )
        if target_name.lower().startswith('portuguese'):
            system_prompt = (
                'Você é um tradutor profissional de dublagem.\n'
                'Traduza do inglês para português (Brasil).\n'
                f'Mantenha as marcas, modelos e números intactos.'
                f'{dur_instruction_pt}\n'
                'Retorne APENAS a tradução sem aspas ou introduções.'
            )
        else:
            system_prompt = (
                f'You are an expert audio dubbing translator into '
                f'{target_name}.\n'
                f'Translate the text naturally and concisely for timing.'
                f'{dur_instruction_en}\n'
                'Output ONLY the translation. No quotes, no explanations.'
            )
        raw = self.generate(text, system=system_prompt).strip()
        if raw.startswith('[') and raw.endswith(']'):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list) and len(parsed) == 1:
                    return [str(parsed[0]).strip()]
            except json.JSONDecodeError:
                pass
        return [raw.strip('\'"')]

    def _translate_batch(
        self,
        chunk: list[str],
        target_language: str,
        durations: list[float] | None = None,
    ) -> list[str]:
        if not chunk:
            return []
        if len(chunk) == 1:
            dur = durations[0] if durations and len(durations) > 0 else None
            return self._translate_single(chunk[0], target_language, dur)

        target_name = _format_language_name(target_language)
        lines = []
        for idx, text in enumerate(chunk):
            dur = (
                durations[idx] if durations and idx < len(durations) else None
            )
            timing = f' [{dur:.1f}s]' if dur is not None else ''
            lines.append(f'{idx}{timing}: {text}')
        numbered_lines = '\n'.join(lines)

        timing_pt = (
            '\nAdapte cada fala para caber no tempo indicado entre colchetes '
            '(ex: [3.2s]). Seja conciso para dublagem sincronizada.'
            if durations
            else ''
        )
        timing_en = (
            '\nAdapt each spoken line to fit the duration indicated in '
            'brackets (e.g. [3.2s]). Be concise for synchronized dubbing.'
            if durations
            else ''
        )
        if target_name.lower().startswith('portuguese'):
            system_prompt = (
                'Você é um tradutor profissional para Português do Brasil.\n'
                'Traduza cada linha numerada para português (Brasil).\n'
                f'Mantenha as marcas, modelos e números intactos.{timing_pt}\n'
                'Mantenha o mesmo número de linhas (ex: "0: tradução"). '
                'Não repita em inglês.\n'
                'Retorne APENAS as linhas numeradas sem introdução.'
            )
        else:
            system_prompt = (
                f'You are a translator into {target_name}.\n'
                f'Translate each numbered line naturally and concisely.'
                f'{timing_en}\n'
                'Preserve proper names, technical terms, and numbers.\n'
                'Maintain exact line numbering (e.g. "0: translation").\n'
                'Output ONLY numbered lines with no preamble.'
            )
        raw_output = self.generate(numbered_lines, system=system_prompt)

        line_results = _parse_numbered_lines(raw_output, len(chunk))
        if all(r is not None for r in line_results):
            has_untranslated = any(
                r.strip().lower() == orig.strip().lower()
                for r, orig in zip(line_results, chunk)
                if r is not None
            )
            if not has_untranslated:
                return [r for r in line_results if r is not None]

        json_results = _parse_json_list(raw_output, len(chunk))
        if json_results is not None:
            has_untranslated = any(
                r.strip().lower() == orig.strip().lower()
                for r, orig in zip(json_results, chunk)
            )
            if not has_untranslated:
                return json_results

        final_results: list[str] = []
        for idx, text in enumerate(chunk):
            val = line_results[idx]
            if val is None or val.strip().lower() == text.strip().lower():
                dur = (
                    durations[idx]
                    if durations and idx < len(durations)
                    else None
                )
                val = self._translate_single(text, target_language, dur)[0]
            final_results.append(val)
        return final_results
