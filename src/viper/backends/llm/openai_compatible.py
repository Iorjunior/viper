"""OpenAI-compatible LLM backend for OpenAI, Ollama, vLLM, and others."""

import json
import re
from typing import override

from openai import OpenAI

from viper.backends.llm.base import LLMBackend
from viper.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


class OpenAICompatibleBackend(LLMBackend):
    """Universal LLM client for any OpenAI-compatible API endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> None:
        self.base_url = (
            base_url if base_url is not None else (OPENAI_BASE_URL or None)
        )
        self.api_key = api_key or OPENAI_API_KEY or 'dummy'
        self.model = model or OPENAI_MODEL
        self.temperature = temperature
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        return self._client

    @override
    def generate(self, prompt: str, system: str = '') -> str:
        client = self._get_client()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({'role': 'system', 'content': system})
        messages.append({'role': 'user', 'content': prompt})

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.temperature,
        )

        choice = response.choices[0]
        return str(choice.message.content or '').strip()

    @override
    def translate(
        self,
        segments: list[str],
        target_language: str,
        durations: list[float] | None = None,
    ) -> list[str]:
        if not segments:
            return []

        system_prompt = (
            f'You are an expert audio dubbing translator into '
            f'{target_language}. '
            'Translate each segment naturally and concisely for timing. '
            'Output ONLY a valid JSON list of translated strings matching '
            'the exact input count. No extra text.'
        )

        user_content = json.dumps(segments, ensure_ascii=False)
        raw_output = self.generate(user_content, system=system_prompt)

        try:
            parsed = json.loads(raw_output)
            if isinstance(parsed, list) and len(parsed) == len(segments):
                return [str(s).strip() for s in parsed]
        except json.JSONDecodeError:
            pass

        match = re.search(r'\[.*\]', raw_output, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list) and len(parsed) == len(segments):
                    return [str(s).strip() for s in parsed]
            except json.JSONDecodeError:
                pass

        lines = [
            line.strip('- *"\t')
            for line in raw_output.splitlines()
            if line.strip()
        ]
        if len(lines) == len(segments):
            return lines

        return segments
