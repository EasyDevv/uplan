import inspect
import json
from rich.console import Console
from rich.json import JSON as RichJSON
from pathlib import Path
from typing import Any, Callable, Dict


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
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
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
