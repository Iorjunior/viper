"""Decorator for declaring pipeline stages with automatic introspection."""

import functools
import inspect
from collections.abc import Callable
from typing import Any

from viper.engine.registry import StageRegistry, global_registry


def stage(
    name: str | None = None,
    description: str = '',
    registry: StageRegistry | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorate a function as an executable Viper processing stage."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        stage_name = name or fn.__name__
        stage_desc = description or (inspect.getdoc(fn) or '').strip()

        sig = inspect.signature(fn)
        inputs_meta: dict[str, Any] = {}
        for param_name, param in sig.parameters.items():
            if param_name in {'self', 'cls'}:
                continue
            param_type = (
                param.annotation.__name__
                if hasattr(param.annotation, '__name__')
                else str(param.annotation)
            )
            inputs_meta[param_name] = {
                'type': param_type if param_type != '_empty' else 'Any',
                'has_default': param.default is not inspect.Parameter.empty,
                'default': (
                    param.default
                    if param.default is not inspect.Parameter.empty
                    else None
                ),
            }

        target_registry = registry or global_registry
        definition = target_registry.register(
            name=stage_name,
            fn=fn,
            description=stage_desc,
            inputs=inputs_meta,
        )

        setattr(fn, '__stage_definition__', definition)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        return wrapper

    return decorator
