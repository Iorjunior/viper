"""Dynamic variable and asset interpolator for DAG pipelines."""

import re
from typing import Any

# Matches an exact single variable expression, e.g., "{{ inputs.video_url }}"
EXACT_VAR_PATTERN = re.compile(r'^\s*\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}\s*$')
# Matches any embedded variable expressions in a longer string
EMBEDDED_VAR_PATTERN = re.compile(r'\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}')


def _get_nested_value(path: str, context: dict[str, Any]) -> Any:
    """Traverse dot-delimited path inside context dictionary."""
    parts = path.split('.')
    current: Any = context
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
    return current


def resolve_template(template: Any, context: dict[str, Any]) -> Any:
    """Resolve a single template expression against the runtime context."""
    if not isinstance(template, str):
        return template

    exact_match = EXACT_VAR_PATTERN.match(template)
    if exact_match:
        var_path = exact_match.group(1)
        val = _get_nested_value(var_path, context)
        return val if val is not None else template

    def _replace(match: re.Match[str]) -> str:
        var_path = match.group(1)
        val = _get_nested_value(var_path, context)
        return str(val) if val is not None else match.group(0)

    return EMBEDDED_VAR_PATTERN.sub(_replace, template)


def resolve_inputs(
    raw_inputs: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    """Recursively resolve all template expressions in a dictionary."""
    resolved: dict[str, Any] = {}
    for key, value in raw_inputs.items():
        if isinstance(value, dict):
            resolved[key] = resolve_inputs(value, context)
        elif isinstance(value, list):
            resolved[key] = [resolve_template(item, context) for item in value]
        else:
            resolved[key] = resolve_template(value, context)
    return resolved
