"""Text processing and translation stages."""

from typing import Any

from viper.backends.resolver import get_llm
from viper.engine.decorator import stage


@stage(
    name='translate',
    description='Translate speech segments to target language using LLM',
)
def translate(
    texts: list[str],
    target_language: str = 'pt-BR',
) -> dict[str, Any]:
    """Translate list of text chunks matching audio timing."""
    llm_backend = get_llm()
    translated = llm_backend.translate(texts, target_language=target_language)
    return {'translated_texts': translated}
