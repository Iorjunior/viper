"""Apple Silicon MLX LM backend for local language models."""

import json
import re
from typing import Any, override

from viper.backends.llm.base import LLMBackend

try:
    from mlx_lm import generate, load
except ImportError:
    generate = None  # type: ignore[assignment]
    load = None  # type: ignore[assignment]

DEFAULT_MLX_MODEL = 'mlx-community/Qwen2.5-1.5B-Instruct-4bit'


class MlxLmBackend(LLMBackend):
    """LLM implementation utilizing Apple Silicon MLX hardware acceleration."""

    def __init__(self, model: str = DEFAULT_MLX_MODEL) -> None:
        self.model_name = model
        self._model: Any = None
        self._tokenizer: Any = None

    def _load_model(self) -> tuple[Any, Any]:
        if load is None:
            msg = 'mlx-lm is not installed. Install with uv sync --extra apple'
            raise ImportError(msg)

        if self._model is None or self._tokenizer is None:
            self._model, self._tokenizer = load(self.model_name)
        return self._model, self._tokenizer

    @override
    def generate(self, prompt: str, system: str = '') -> str:
        if generate is None:
            msg = 'mlx-lm is not installed. Install with uv sync --extra apple'
            raise ImportError(msg)

        model, tokenizer = self._load_model()

        messages: list[dict[str, str]] = []
        if system:
            messages.append({'role': 'system', 'content': system})
        messages.append({'role': 'user', 'content': prompt})

        if hasattr(tokenizer, 'apply_chat_template'):
            formatted_prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            formatted_prompt = f'{system}\n\n{prompt}' if system else prompt

        output = generate(
            model,
            tokenizer,
            prompt=formatted_prompt,
            max_tokens=1024,
            verbose=False,
        )
        return str(output).strip()

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
