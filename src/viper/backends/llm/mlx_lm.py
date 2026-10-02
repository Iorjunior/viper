"""Apple Silicon MLX LM backend for local language models."""

from typing import Any, override

from viper.backends.llm.base import LLMBackend

try:
    from mlx_lm import generate, load, stream_generate
    from mlx_lm.sample_utils import make_sampler
except ImportError:
    generate = None  # type: ignore[assignment]
    load = None  # type: ignore[assignment]
    stream_generate = None  # type: ignore[assignment]
    make_sampler = None  # type: ignore[assignment]

DEFAULT_MLX_MODEL = 'mlx-community/translategemma-4b-it-4bit'


def _resolve_stop_token_ids(tokenizer: Any) -> set[int]:
    stop_ids: set[int] = set()
    eos = getattr(tokenizer, 'eos_token_id', None)
    if isinstance(eos, int):
        stop_ids.add(eos)
    elif isinstance(eos, (list, tuple, set)):
        stop_ids.update(eos)

    for word in ('<end_of_turn>', '<|im_end|>', '<|endoftext|>'):
        try:
            tok = tokenizer.convert_tokens_to_ids(word)
            if isinstance(tok, int) and tok >= 0:
                stop_ids.add(tok)
        except Exception:
            pass
    return stop_ids


def _build_chat_prompt(
    model_name: str, tokenizer: Any, prompt: str, system: str
) -> str:
    if 'translategemma' in model_name.lower():
        sys_part = f'{system}\n\n\n' if system else ''
        return (
            f'<start_of_turn>user\n'
            f'{sys_part}{prompt}<end_of_turn>\n'
            f'<start_of_turn>model\n'
        )

    if hasattr(tokenizer, 'apply_chat_template'):
        messages: list[dict[str, str]] = []
        if system:
            messages.append({'role': 'system', 'content': system})
        messages.append({'role': 'user', 'content': prompt})
        try:
            return str(
                tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            )
        except Exception:
            pass

    return f'{system}\n\n{prompt}' if system else prompt


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
        if stream_generate is None:
            msg = 'mlx-lm is not installed. Install with uv sync --extra apple'
            raise ImportError(msg)

        model, tokenizer = self._load_model()
        formatted_prompt = _build_chat_prompt(
            self.model_name, tokenizer, prompt, system
        )
        stop_token_ids = _resolve_stop_token_ids(tokenizer)

        sampler = make_sampler(temp=0.0) if make_sampler else None
        collected: list[str] = []
        for resp in stream_generate(
            model,
            tokenizer,
            prompt=formatted_prompt,
            max_tokens=512,
            sampler=sampler,
        ):
            if (
                resp.token in stop_token_ids
                or '<end_of_turn>' in resp.text
                or '<|im_end|>' in resp.text
                or '<|endoftext|>' in resp.text
            ):
                break
            collected.append(resp.text)

        output_str = ''.join(collected).strip()
        stop_tokens = (
            '<end_of_turn>',
            '<start_of_turn>',
            '<|im_end|>',
            '<|endoftext|>',
        )
        for stop in stop_tokens:
            if stop in output_str:
                output_str = output_str.split(stop, 1)[0].strip()

        return output_str
