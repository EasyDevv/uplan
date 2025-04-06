import logging
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import ValidationError

from uplan.utils.logging.trace.context import LogContext
from uplan.utils.logging.trace.colors import get_color, build_indent
from uplan.utils.logging.trace.helpers import pretty_json


def format_with_tree_indent(message: str, depth: int, event_type: str) -> str:
    """
    Apply tree indentation and prefix symbols to a multi-line log message.

    Args:
        message: The pure log message without indentation.
        depth: The call depth for indentation.
        event_type: One of 'entry', 'exit', 'error'.

    Returns:
        The message decorated with tree indentation and symbols.
    """

    color = get_color(depth)
    indent = build_indent(depth)

    # Determine prefix symbols based on event type
    if event_type == "entry":
        first_prefix = f"{indent}[{color}]├──[/] "
        child_prefix = f"{indent}[{color}]│   [/] "
    elif event_type == "exit":
        first_prefix = f"{indent}[{color}]└──[/] "
        child_prefix = f"{indent}[{color}]    [/] "
    elif event_type == "error":
        first_prefix = f"{indent}[{color}]└──[/] "
        child_prefix = f"{indent}[{color}]│   [/] "
    else:
        first_prefix = indent
        child_prefix = indent

    lines = message.splitlines()
    if not lines:
        return ""

    decorated_lines = [f"{first_prefix}{lines[0]}"]
    decorated_lines += [f"{child_prefix}{line}" for line in lines[1:]]
    return "\n".join(decorated_lines)


def log_entry(
    logger: logging.Logger,
    level: int,
    func_name: str,
    module_name: str,
    class_name: Optional[str],
    is_async: bool,
    call_args: Dict[str, Any],
    location: str,
    depth: int,
) -> None:
    context = LogContext(
        event_type="entry",
        function_name=func_name,
        module_name=module_name,
        class_name=class_name,
        is_async=is_async,
        details={"call_args": call_args},
        depth=depth,
    )
    color = get_color(depth)

    sync_async = "async" if is_async else "sync"
    name = f"{class_name}.{func_name}" if class_name else func_name
    depth_str = f"[[{color}]Depth:{depth}[/]]"
    colored_name = f"[bold {color}]{name}[/]"
    colored_location = f"[{color}]{location}[/]"

    args_to_format = {k: v for k, v in call_args.items() if k != "self"}
    # No indent in pretty_json, pure content only
    args_json_str = pretty_json(args_to_format, "", "")

    core_parts = [
        f"{depth_str} 🟢 Entry {sync_async} {colored_name}",
        "Args:",
        args_json_str,
        f"Location: {colored_location}",
    ]
    core_message = "\n".join(m for m in core_parts if m and m.strip())
    message = format_with_tree_indent(core_message, depth, "entry")

    try:
        logger.log(level, message, extra={"log_context": context})
    except ValidationError as e:
        logger.error(
            f"Pydantic validation error for {name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )
    except Exception as e:
        logger.error(
            f"Error during logging for {name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )


def log_exit(
    logger: logging.Logger,
    level: int,
    func_name: str,
    module_name: str,
    class_name: Optional[str],
    is_async: bool,
    elapsed: float,
    depth: int,
) -> None:
    context = LogContext(
        event_type="exit",
        function_name=func_name,
        module_name=module_name,
        class_name=class_name,
        is_async=is_async,
        execution_time_seconds=elapsed,
        depth=depth,
    )
    color = get_color(depth)

    sync_async = "async" if is_async else "sync"
    name = f"{class_name}.{func_name}" if class_name else func_name
    depth_str = f"[[{color}]Depth:{depth}[/]]"
    colored_name = f"[bold {color}]{name}[/]"

    core_message = f"{depth_str} 🏿 Exit {sync_async} {colored_name} in {elapsed:.4f}s"
    message = format_with_tree_indent(core_message, depth, "exit")

    try:
        logger.log(level, message, extra={"log_context": context})
    except ValidationError as e:
        logger.error(
            f"Pydantic validation error for {name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )
    except Exception as e:
        logger.error(
            f"Error during logging for {name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )


def log_error(
    logger: logging.Logger,
    func_name: str,
    module_name: str,
    class_name: Optional[str],
    is_async: bool,
    elapsed: float,
    exception: Exception,
    call_args: Dict[str, Any],
    location: str,
    depth: int,
) -> None:
    import traceback

    tb = exception.__traceback__
    extracted_tb = traceback.extract_tb(tb)
    precise_location = location
    if extracted_tb:
        last_frame = extracted_tb[-1]
        try:
            p = Path(last_frame.filename)
            precise_location = f"{p.parent.name}/{p.name}:{last_frame.lineno}"
        except Exception:
            precise_location = f"{last_frame.filename}:{last_frame.lineno}"

    context = LogContext(
        event_type="error",
        function_name=func_name,
        module_name=module_name,
        class_name=class_name,
        is_async=is_async,
        execution_time_seconds=elapsed,
        error_type=type(exception).__name__,
        error_message=str(exception),
        details={"call_args": call_args, "location": precise_location},
        depth=depth,
    )
    color = get_color(depth)

    sync_async = "async" if is_async else "sync"
    name = f"{class_name}.{func_name}" if class_name else func_name
    depth_str = f"[[{color}]Depth:{depth}[/]]"
    colored_name = f"[bold {color}]{name}[/]"
    colored_location = f"[{color}]{precise_location}[/]"

    args_to_format = {k: v for k, v in call_args.items() if k != "self"}
    args_json_str = pretty_json(args_to_format, "", "")

    core_parts = [
        f"{depth_str} 🟥 [bold red]Error[/] in {sync_async} {colored_name} after {elapsed:.4f}s",
        "Args:",
        args_json_str,
        f"Location: {colored_location}",
        f"[bold red]{type(exception).__name__}:[/] [red]{exception}[/]",
    ]
    core_message = "\n".join(m for m in core_parts if m and m.strip())
    message = format_with_tree_indent(core_message, depth, "error")

    try:
        logger.log(logging.ERROR, message, extra={"log_context": context})
    except ValidationError as e:
        logger.error(
            f"Pydantic validation error during error logging for {name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )
    except Exception as e:
        logger.error(
            f"Error during error logging for {name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )
