"""Abstract base class for Large Language Model backends."""

from abc import ABC, abstractmethod


class LLMBackend(ABC):
    """Abstract interface for LLM backends (translation and generation)."""

    @abstractmethod
    def translate(
        self,
        segments: list[str],
        target_language: str,
        durations: list[float] | None = None,
    ) -> list[str]:
        """Translate a list of text segments to target language."""

    @abstractmethod
    def generate(self, prompt: str, system: str = '') -> str:
        """Generate text response given a prompt and optional instructions."""
