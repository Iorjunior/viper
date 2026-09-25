"""LLM backend contracts and implementations."""

from viper.backends.llm.base import LLMBackend
from viper.backends.llm.openai_compatible import OpenAICompatibleBackend

__all__ = [
    'LLMBackend',
    'OpenAICompatibleBackend',
]
