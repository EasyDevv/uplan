import inspect
import json
from rich.console import Console
from rich.json import JSON as RichJSON
from pathlib import Path
from typing import Any, Callable, Dict

MAX_JSON_PREVIEW_LENGTH = 50


def format_call_args(func: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
    """
    Format function call arguments into a dictionary.

    Args:
        func: The function being called.
        args: Positional arguments.
        kwargs: Keyword arguments.

    Returns:
        Dictionary of argument names to their string representations.
    """
    try:
        bound = inspect.signature(func).bind(*args, **kwargs)
        bound.apply_defaults()
        return {
            k: str(v) if isinstance(v, Path) else repr(v)
            for k, v in bound.arguments.items()
        }
    except Exception:
        return {"args": repr(args), "kwargs": repr(kwargs)}


def _truncate_long_strings(obj: Any, max_length: int = MAX_JSON_PREVIEW_LENGTH) -> Any:
    """
    Recursively truncate long strings in dicts, lists, tuples, and sets.

    Args:
        obj: The object to process.
        max_length: Maximum allowed string length before truncation.

    Returns:
        A copy of the object with long strings truncated and suffixed with '...'.
    """
    if isinstance(obj, dict):
        return {
            (
                _truncate_long_strings(k, max_length) if isinstance(k, str) else k
            ): _truncate_long_strings(v, max_length)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [_truncate_long_strings(item, max_length) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_truncate_long_strings(item, max_length) for item in obj)
    elif isinstance(obj, set):
        return {_truncate_long_strings(item, max_length) for item in obj}
    elif isinstance(obj, str):
        if len(obj) > max_length:
            return obj[:max_length] + " ..."
        return obj
    else:
        return obj


def pretty_json(data: dict, first_prefix: str, child_prefix: str) -> str:
    """
    Convert a dictionary to a pretty-printed JSON string with prefixed indentation using rich,
    preserving nested indentation.

    Args:
        data: The dictionary to convert.
        first_prefix: Prefix string for the first line (tree branch).
        child_prefix: Prefix string for subsequent lines (tree vertical continuation).

    Returns:
        Indented JSON string with rich formatting.
    """
    try:
        truncated_data = _truncate_long_strings(data, MAX_JSON_PREVIEW_LENGTH)
        json_str = json.dumps(truncated_data, indent=2, ensure_ascii=False)
        console = Console(record=True, width=120)
        console.print(RichJSON(json_str, indent=2, ensure_ascii=False))
        pretty = console.export_text()
        lines = pretty.splitlines()
        if not lines:
            return ""
        result_lines = []
        for idx, line in enumerate(lines):
            if idx == 0:
                result_lines.append(f"{first_prefix}{line}")
            else:
                leading_spaces = len(line) - len(line.lstrip(" "))
                result_lines.append(
                    f"{child_prefix}{' ' * leading_spaces}{line.lstrip(' ')}"
                )
        return "\n".join(result_lines)
    except TypeError as e:
        return f"{first_prefix}{{... serialization error: {e} ...}}"
    except Exception as e:
        return f"{first_prefix}{{... unknown error during json dump: {e} ...}}"
