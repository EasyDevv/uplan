"""
Comprehensive logging utilities for uPlan.

This module provides:
- Automated function execution tracing
- Structured log file storage
- Execution time monitoring
- Error capturing with full tracebacks
"""

import functools
import inspect
import json
import logging
import time
import traceback
import contextvars
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Union, Set

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

# Initialize rich console and install rich traceback handler
console = Console()
install_rich_traceback(show_locals=True)

# Global variables
DEFAULT_LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(message)s"
LOG_DIR = Path("logs")

# Create logs directory if it doesn't exist
LOG_DIR.mkdir(exist_ok=True)

# Context variable to store current function name
current_func_name = contextvars.ContextVar("current_func_name", default=None)

# Track logged errors to prevent duplicates
# Use contextvars to ensure thread safety
logged_errors = contextvars.ContextVar("logged_errors", default=set())


@dataclass
class MetricsData:
    """Container for performance metrics data."""

    count: int = 0
    total_time: float = 0
    avg_time: float = 0
    max_time: float = 0

    def update(self, execution_time: float) -> None:
        """Update metrics with new execution time."""
        self.count += 1
        self.total_time += execution_time
        self.avg_time = self.total_time / self.count
        self.max_time = max(self.max_time, execution_time)


class StructuredLogRecord(logging.LogRecord):
    """Extended LogRecord that adds structured data for JSON logging."""

    def __init__(self, *args, **kwargs):
        """Initialize with standard LogRecord args and extend with structured data."""
        super().__init__(*args, **kwargs)
        self.structured_data = {}

        # Automatically include current function name from context if available
        func_name = current_func_name.get()
        if func_name is not None:
            self.funcName = func_name


class StructuredLogger(logging.Logger):
    """Logger that supports structured data logging."""

    def makeRecord(
        self,
        name,
        level,
        fn,
        lno,
        msg,
        args,
        exc_info,
        func=None,
        extra=None,
        sinfo=None,
    ):
        """Create a LogRecord with structured data support."""
        rv = StructuredLogRecord(name, level, fn, lno, msg, args, exc_info, func, sinfo)

        # Add function name from context automatically if not explicitly provided
        if extra is None:
            extra = {}

        if "function" not in extra:
            func_name = current_func_name.get()
            if func_name is not None:
                extra["function"] = func_name

        if extra is not None:
            for key in extra:
                if key in ["message", "asctime"]:
                    raise KeyError(f"Attempt to overwrite {key} in LogRecord")
                if key == "structured_data" and hasattr(rv, "structured_data"):
                    rv.structured_data.update(extra[key])
                else:
                    rv.__dict__[key] = extra[key]
        return rv


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": super().format(record),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "structured_data") and record.structured_data:
            log_data.update(record.structured_data)

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_data)


def get_call_info(func: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
    """Get common call information for function tracing."""
    frame = (
        inspect.currentframe().f_back.f_back
    )  # Two frames back to get the actual caller
    filename = frame.f_code.co_filename if frame else "unknown"
    lineno = frame.f_lineno if frame else 0

    call_args = [f"{repr(arg)}" for arg in args]
    call_args.extend(f"{key}={repr(value)}" for key, value in kwargs.items())
    call_signature = f"{func.__name__}({', '.join(call_args)})"

    return {
        "function": func.__name__,
        "module": func.__module__,
        "caller": f"{filename}:{lineno}",
        "call_signature": call_signature,
    }


def get_error_hash(error: Exception, func_name: str) -> str:
    """
    Generate a unique hash for an error to prevent duplicate logging.

    Args:
        error: The exception that was raised
        func_name: Name of the function where error occurred

    Returns:
        str: A unique hash for this error
    """
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    hash_content = f"{func_name}:{str(error)}:{''.join(tb[-3:])}"
    return hashlib.md5(hash_content.encode()).hexdigest()


def is_error_logged(error: Exception, func_name: str) -> bool:
    """
    Check if this particular error has already been logged.

    Args:
        error: The exception to check
        func_name: Function where the error occurred

    Returns:
        bool: True if this error has already been logged
    """
    error_hash = get_error_hash(error, func_name)
    error_set = logged_errors.get()
    return error_hash in error_set


def mark_error_logged(error: Exception, func_name: str) -> None:
    """
    Mark an error as logged to prevent duplicate logging.

    Args:
        error: The exception that was logged
        func_name: Function where the error occurred
    """
    error_hash = get_error_hash(error, func_name)
    error_set = logged_errors.get()
    new_set = error_set.copy()
    new_set.add(error_hash)
    logged_errors.set(new_set)


def log_function_event(
    event_type: str,
    call_info: Dict[str, Any],
    elapsed: Optional[float] = None,
    error: Optional[Exception] = None,
    is_async: bool = False,
) -> None:
    """Log function-related events with consistent formatting."""
    prefix = "async " if is_async else ""
    func_name = call_info["function"]

    if event_type == "entry":
        console.print(
            f"▶️ Entering {prefix}{func_name} from {call_info['caller']}",
            style="bright_blue",
        )
        log_structured("function_entry", **call_info, is_async=is_async)
    elif event_type == "exit":
        console.print(
            f"✅ Exited {prefix}{func_name} in {elapsed:.4f}s",
            style="green",
        )
        log_structured(
            "function_exit",
            **call_info,
            status="success",
            execution_time=elapsed,
            is_async=is_async,
        )
    elif event_type == "error":
        # Check if this error has been logged already
        if is_error_logged(error, func_name):
            return

        # Log the error and mark it as logged
        error_msg = f"❌ Error in {prefix}{func_name}:"
        details = str(error)
        tb_str = traceback.format_exc()
        console.print(
            f"{error_msg}\n{details}\n{tb_str}",
            style="bold red",
        )
        log_structured(
            "function_error",
            **call_info,
            status="error",
            execution_time=elapsed,
            error=str(error),
            traceback=tb_str,
            is_async=is_async,
        )

        # Mark this error as logged to prevent duplicates
        mark_error_logged(error, func_name)


def setup_logging(level: Optional[int] = None) -> logging.Logger:
    """Set up logging with both console and file handlers."""
    log_level = level or DEFAULT_LOG_LEVEL
    logging.setLoggerClass(StructuredLogger)

    logger = logging.getLogger("uplan")

    # Only set up logging if it hasn't already been configured
    if not logger.hasHandlers():
        logger.setLevel(log_level)

        # Console handler with rich formatting
        console_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_path=False,
            log_time_format="[%X]",
        )
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)

        # JSON file handler for structured logging
        log_file = LOG_DIR / f"uplan_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JSONFormatter(LOG_FORMAT))
        logger.addHandler(file_handler)
    else:
        # If handlers exist but level needs to be changed
        if logger.level != log_level:
            logger.setLevel(log_level)
            for handler in logger.handlers:
                handler.setLevel(log_level)

    return logger


# Create global logger instance - will only set up once
_logger = setup_logging()


def get_logger() -> logging.Logger:
    """Get the uplan logger instance."""
    return _logger


def log_structured(log_type: str, **kwargs) -> None:
    """Add structured log entry with custom fields."""
    logger = get_logger()
    # Create log entry data without nesting under structured_data
    log_data = {"type": log_type, **kwargs}
    # Pass directly to structured_data
    logger.info("", extra={"structured_data": log_data})


def trace_function(func: Callable) -> Callable:
    """Decorator to trace entry and exit of a function with timing."""
    func_name = func.__name__

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Set context variable for this execution
        token = current_func_name.set(func_name)

        try:
            call_info = get_call_info(func, args, kwargs)
            log_function_event("entry", call_info)

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                log_function_event("exit", call_info, time.time() - start_time)
                return result
            except Exception as e:
                log_function_event("error", call_info, time.time() - start_time, e)
                raise
        finally:
            # Reset context variable
            current_func_name.reset(token)

    return wrapper


def log_async_function(func: Callable) -> Callable:
    """Decorator to trace entry and exit of an async function with timing."""
    func_name = func.__name__

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Set context variable for this execution
        token = current_func_name.set(func_name)

        try:
            call_info = get_call_info(func, args, kwargs)
            log_function_event("entry", call_info, is_async=True)

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                log_function_event(
                    "exit", call_info, time.time() - start_time, is_async=True
                )
                return result
            except Exception as e:
                log_function_event(
                    "error", call_info, time.time() - start_time, e, is_async=True
                )
                raise
        finally:
            # Reset context variable
            current_func_name.reset(token)

    return wrapper


def log_command(cmd_args: list) -> None:
    """Log a command execution."""
    log_structured("command_execution", command=" ".join(cmd_args))


def log_error(error: Exception, module: Optional[str] = None) -> None:
    """Log an error with full traceback."""
    # Skip if this error has already been logged
    if module and is_error_logged(error, module):
        return

    error_time = datetime.now()
    tb = traceback.format_exc()

    # Log to console with full traceback
    console.print(f"❌ Error: {str(error)}\n{tb}")

    # Log to structured log
    log_structured(
        "error", message=str(error), module=module or "unknown", traceback=tb
    )

    # Create detailed error report file
    error_dir = LOG_DIR / "errors"
    error_dir.mkdir(exist_ok=True)
    error_filename = (
        f"error_{error_time.strftime('%Y%m%d_%H%M%S')}_{module or 'unknown'}.log"
    )
    error_file = error_dir / error_filename

    with open(error_file, "w") as f:
        f.write("=== uPlan Error Report ===\n")
        f.write(f"Timestamp: {error_time.isoformat()}\n")
        f.write(f"Module: {module or 'unknown'}\n")
        f.write(f"Error: {error.__class__.__name__}: {str(error)}\n\n")
        f.write(f"=== Traceback ===\n{tb}\n")

        # Include exception chain if present
        if error.__cause__:
            f.write("\n=== Cause Chain ===\n")
            cause = error.__cause__
            while cause:
                f.write(f"{cause.__class__.__name__}: {str(cause)}\n")
                cause = cause.__cause__

    console.print(f"📝 Error report: {error_file}", style="yellow")

    # Mark this error as logged
    if module:
        mark_error_logged(error, module)
