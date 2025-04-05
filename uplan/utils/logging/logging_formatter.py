import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

# Attempt to import LogContext from logging_trace
try:
    from .logging_trace import LogContext
except ImportError:

    class LogContext(BaseModel):
        pass


# --- JSON serialization helper ---
def safe_serialize(obj: Any) -> Any:
    """Safely converts an object to a JSON serializable format."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json", exclude_none=True)
    if isinstance(obj, (datetime, Path)):
        return obj.isoformat() if isinstance(obj, datetime) else str(obj)
    try:
        return json.dumps(obj)
    except (TypeError, OverflowError):
        return repr(obj)


# --- JSON formatter ---
class JsonFormatter(logging.Formatter):
    """Formats log records as JSON."""

    def __init__(self, fmt_keys: Optional[Dict[str, str]] = None):
        """
        Initializes JsonFormatter.

        Args:
            fmt_keys: A dictionary mapping log record attributes to JSON keys.
                      Defaults to the standard mapping if None.
        """
        super().__init__()
        self.fmt_keys = fmt_keys or {
            "level": "levelname",
            "logger": "name",
            "module": "module",
            "function": "funcName",
            "line": "lineno",
            "thread_name": "threadName",
        }
        # ISO 8601-like format (UTC)
        self.default_time_format = "%Y-%m-%dT%H:%M:%S"
        self.default_msec_format = "%s.%03dZ"

    def formatTime(
        self, record: logging.LogRecord, datefmt: Optional[str] = None
    ) -> str:
        """
        Converts the creation time of the log record to a UTC ISO 8601 formatted string.

        Args:
            record: The log record to format.
            datefmt: The date format to use (ignored, always uses UTC ISO format).

        Returns:
            The formatted time string.
        """
        utc_ct = datetime.fromtimestamp(record.created, tz=timezone.utc)
        t = utc_ct.strftime(self.default_time_format)
        return self.default_msec_format % (t, record.msecs)

    def format(self, record: logging.LogRecord) -> str:
        """
        Formats the given log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A JSON formatted log string.
        """
        log_entry: Dict[str, Any] = {"timestamp": self.formatTime(record)}

        # Always include source location info
        log_entry["location"] = f"{record.pathname}:{record.lineno}"

        # Add standard log attributes based on fmt_keys
        for key, val_key in self.fmt_keys.items():
            val = getattr(record, val_key, None)
            if val is not None:
                log_entry[key] = val

        # Handle message (use as-is if dict/list, otherwise call getMessage())
        log_entry["message"] = (
            record.getMessage()
            if not isinstance(record.msg, (dict, list))
            else record.msg
        )

        # Handle LogContext
        log_context_data = None
        if hasattr(record, "log_context") and isinstance(
            record.log_context, LogContext
        ):
            try:
                log_context_data = record.log_context.model_dump(
                    mode="json", exclude_none=True
                )
                log_entry.update(log_context_data)
            except Exception as e:
                log_entry["log_context_serialization_error"] = repr(e)

        # Handle additional data (extra)
        standard_attrs = list(logging.LogRecord.__dict__.keys()) + [
            "message",
            "asctime",
            "relativeCreated",
            "log_context",
            "args",  # args are used in getMessage(), so excluded
        ]
        extra_data = {}
        for k, v in record.__dict__.items():
            is_standard = k in standard_attrs
            is_internal = k.startswith("_")
            is_from_log_context = log_context_data and k in log_context_data
            # Consider as extra if not standard, internal, or already processed from LogContext
            if not is_standard and not is_internal and not is_from_log_context:
                extra_data[k] = v
        if extra_data:
            # Safely serialize extra data
            log_entry["extra_data"] = {
                k: safe_serialize(v) for k, v in extra_data.items()
            }

        # Handle exception info
        if record.exc_info:
            traceback_str = self.formatException(record.exc_info)
            exc_type, exc_value, _ = (
                record.exc_info
            )  # Keep original extraction for type/message
            log_entry["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
                "traceback": traceback_str,  # Always include traceback
            }
        elif record.exc_text:  # Use exc_text if no exc_info
            log_entry["exception_text"] = record.exc_text
        if record.stack_info:  # Add stack info if present
            log_entry["stack_info"] = record.stack_info

        # Final JSON serialization
        try:
            return json.dumps(log_entry, default=safe_serialize, ensure_ascii=False)
        except Exception as e:
            log_entry["json_serialization_error"] = repr(e)
            return json.dumps(log_entry, default=repr, ensure_ascii=False)
