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

from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

# Initialize rich console and install rich traceback handler
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
    logger = get_logger()

    if event_type == "entry":
        structured_data = {"type": "function_entry", **call_info, "is_async": is_async}
        logger.info(
            f"▶️ Entering {prefix}{func_name} from {call_info['caller']}",
            extra={"structured_data": structured_data},
        )
    elif event_type == "exit":
        structured_data = {
            "type": "function_exit",
            **call_info,
            "status": "success",
            "execution_time": elapsed,
            "is_async": is_async,
        }
        logger.info(
            f"✅ Exited {prefix}{func_name} in {elapsed:.4f}s",
            extra={"structured_data": structured_data},
        )
    elif event_type == "error":
        # Check if this error has been logged already
        if is_error_logged(error, func_name):
            return

        # Log the error and mark it as logged
        error_msg = f"❌ Error in {prefix}{func_name}:"
        details = str(error)
        tb_str = traceback.format_exc()

        # Direct logger call with structured data
        structured_data = {
            "type": "function_error",
            **call_info,
            "status": "error",
            "execution_time": elapsed,
            "error": str(error),
            "traceback": tb_str,
            "is_async": is_async,
        }
        # Use logger for error output instead of console.print
        logger.error(
            f"{error_msg}\n{details}",
            exc_info=True,  # Include exception info for rich traceback
            extra={"structured_data": structured_data},
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
