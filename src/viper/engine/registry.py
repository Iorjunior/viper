"""Central registry for discovering and accessing pipeline stages."""

from collections.abc import Callable
from typing import Any

from viper.engine.models import StageDefinition


class StageRegistry:
    """Registry holding all decorated stage implementations."""

    def __init__(self) -> None:
        self._stages: dict[str, StageDefinition] = {}

    def register(
        self,
        name: str,
        fn: Callable[..., Any],
        description: str = '',
        inputs: dict[str, Any] | None = None,
    ) -> StageDefinition:
        """Register a stage function and its metadata."""
        definition = StageDefinition(
            name=name,
            description=description,
            inputs=inputs or {},
            fn=fn,
        )
        self._stages[name] = definition
        return definition

    def get(self, name: str) -> StageDefinition | None:
        """Retrieve a stage definition by unique name."""
        return self._stages.get(name)

    def list_names(self) -> list[str]:
        """List names of all currently registered stages."""
        return list(self._stages.keys())

    def list_stages(self) -> list[StageDefinition]:
        """List all currently registered stage definitions."""
        return list(self._stages.values())


# Global default registry instance
global_registry = StageRegistry()
