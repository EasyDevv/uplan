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
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Union

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
        if extra is not None:
            for key in extra:
                if key in ["message", "asctime"] or key in rv.__dict__:
                    raise KeyError(f"Attempt to overwrite {key} in LogRecord")
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


def log_function_event(
    event_type: str,
    call_info: Dict[str, Any],
    elapsed: Optional[float] = None,
    error: Optional[Exception] = None,
    is_async: bool = False,
) -> None:
    """Log function-related events with consistent formatting."""
    prefix = "async " if is_async else ""
    if event_type == "entry":
        console.print(
            f"▶️ Entering {prefix}{call_info['function']} from {call_info['caller']}",
            style="bright_blue",
        )
        log_structured("function_entry", **call_info, is_async=is_async)
    elif event_type == "exit":
        console.print(
            f"✅ Exited {prefix}{call_info['function']} in {elapsed:.4f}s",
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
        console.print(
            f"❌ Error in {prefix}{call_info['function']}: {str(error)}",
            style="bold red",
        )
        log_structured(
            "function_error",
            **call_info,
            status="error",
            execution_time=elapsed,
            error=str(error),
            traceback=traceback.format_exc(),
            is_async=is_async,
        )


def setup_logging(level: Optional[int] = None) -> logging.Logger:
    """Set up logging with both console and file handlers."""
    log_level = level or DEFAULT_LOG_LEVEL
    logging.setLoggerClass(StructuredLogger)

    logger = logging.getLogger("uplan")
    logger.setLevel(log_level)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler
    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_path=False,
        log_time_format="[%X]",
    )
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

    # File handler
    today = datetime.now().strftime("%Y%m%d")
    log_file = LOG_DIR / f"uplan_{today}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(JSONFormatter(LOG_FORMAT))
    logger.addHandler(file_handler)

    return logger


# Create global logger instance
_logger = setup_logging()


def get_logger() -> logging.Logger:
    """Get the uplan logger instance."""
    return _logger


def log_structured(log_type: str, **kwargs) -> None:
    """Add structured log entry with custom fields."""
    logger = get_logger()
    extra = {"structured_data": {"type": log_type, **kwargs}}
    logger.info("", extra=extra)


def trace_function(func: Callable) -> Callable:
    """Decorator to trace entry and exit of a function with timing."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
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

    return wrapper


def log_async_function(func: Callable) -> Callable:
    """Decorator to trace entry and exit of an async function with timing."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
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

    return wrapper


@contextmanager
def LogContext(context_name: str):
    """Context manager for tracking logical blocks of code."""
    logger = get_logger()
    console.print(f"⏺ Starting context: {context_name}", style="cyan")
    log_structured("context_entry", context=context_name)

    start_time = time.time()
    try:
        yield
        elapsed = time.time() - start_time
        console.print(
            f"✓ Completed context: {context_name} in {elapsed:.4f}s", style="green"
        )
        log_structured(
            "context_exit",
            context=context_name,
            status="success",
            execution_time=elapsed,
        )
    except Exception as e:
        elapsed = time.time() - start_time
        console.print(f"❌ Error in context {context_name}: {str(e)}", style="bold red")
        log_structured(
            "context_error",
            context=context_name,
            status="error",
            execution_time=elapsed,
            error=str(e),
            traceback=traceback.format_exc(),
        )
        raise


class LogAnalyzer:
    """Utility class for analyzing log files."""

    def __init__(self, log_file: Optional[Union[str, Path]] = None):
        """Initialize with a specific log file or today's log file."""
        if log_file is None:
            today = datetime.now().strftime("%Y%m%d")
            self.log_file = LOG_DIR / f"uplan_{today}.log"
        else:
            self.log_file = Path(log_file)

        self._metrics_cache: Dict[str, Dict[str, MetricsData]] = {
            "functions": {},
            "contexts": {},
        }
        self._errors_cache: list = []
        self._cache_updated = False

    def _update_cache(self) -> None:
        """Update the metrics and errors cache from log file."""
        if not self.log_file.exists() or self._cache_updated:
            return

        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    self._process_log_entry(log_entry)
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    console.print(f"Error parsing log entry: {e}", style="red")

        self._cache_updated = True

    def _process_log_entry(self, log_entry: dict) -> None:
        """Process a single log entry for metrics and errors."""
        structured_data = log_entry
        entry_type = structured_data.get("type", "")

        if entry_type == "function_exit":
            self._update_metrics(
                "functions",
                structured_data.get("function", "unknown"),
                structured_data.get("execution_time", 0),
            )
        elif entry_type == "context_exit":
            self._update_metrics(
                "contexts",
                structured_data.get("context", "unknown"),
                structured_data.get("execution_time", 0),
            )
        elif entry_type in ("function_error", "context_error"):
            self._errors_cache.append(
                {
                    "timestamp": log_entry.get("timestamp"),
                    "type": entry_type,
                    "location": f"{structured_data.get('function', structured_data.get('context', 'unknown'))}",
                    "module": structured_data.get("module", "unknown"),
                    "error": structured_data.get("error"),
                    "traceback": structured_data.get("traceback"),
                }
            )

    def _update_metrics(self, category: str, name: str, execution_time: float) -> None:
        """Update metrics for a specific category and name."""
        if name not in self._metrics_cache[category]:
            self._metrics_cache[category][name] = MetricsData()
        self._metrics_cache[category][name].update(execution_time)

    def get_performance_metrics(self) -> Dict[str, Dict[str, dict]]:
        """Get performance metrics from the log file."""
        self._update_cache()
        return {
            category: {name: asdict(data) for name, data in metrics.items()}
            for category, metrics in self._metrics_cache.items()
        }

    def get_error_report(self) -> list:
        """Get a report of errors from the log file."""
        self._update_cache()
        return self._errors_cache

    def print_summary(self) -> None:
        """Print a summary of the log file to the console."""
        console.print("\n[bold blue]====== uPlan Log Analysis ======[/bold blue]")

        metrics = self.get_performance_metrics()
        for category in ("functions", "contexts"):
            if metrics[category]:
                console.print(f"\n[bold]{category.title()} Performance:[/bold]")
                sorted_items = sorted(
                    metrics[category].items(),
                    key=lambda x: x[1]["total_time"],
                    reverse=True,
                )
                for name, data in sorted_items[:10]:
                    console.print(
                        f"  [cyan]{name}[/cyan]: {data['count']} calls, "
                        f"avg: {data['avg_time']:.4f}s, max: {data['max_time']:.4f}s"
                    )

        errors = self.get_error_report()
        if errors:
            console.print(f"\n[bold red]Errors ({len(errors)}):[/bold red]")
            for i, error in enumerate(errors[:5]):
                console.print(
                    f"  {i + 1}. [red]{error['location']}[/red]: {error['error']}"
                )
            if len(errors) > 5:
                console.print(f"  ... and {len(errors) - 5} more errors")
        else:
            console.print("\n[green]No errors reported[/green]")

        console.print("\n[bold blue]================================[/bold blue]")


def log_command(cmd_args: list) -> None:
    """Log a command execution."""
    log_structured("command_execution", command=" ".join(cmd_args))


def log_error(error: Exception, module: Optional[str] = None) -> None:
    """Log an error with full traceback."""
    logger = get_logger()
    tb = traceback.format_exc()
    console.print(f"❌ [bold red]Error:[/bold red] {str(error)}\n{tb}", style="red")
    log_structured(
        "error", message=str(error), module=module or "unknown", traceback=tb
    )
