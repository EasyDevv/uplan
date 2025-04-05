import logging
from datetime import datetime

# Rich imports
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

# Internal imports
from .logging_config import (
    CONSOLE_LOG_LEVEL,
    JSON_LOG_FILENAME_FORMAT,
    JSON_LOG_LEVEL,
    LOG_DIR,
    LOGGER_NAME,
    LOG_DETAIL,
)
from .logging_formatter import JsonFormatter


def configure_console_handler(logger: logging.Logger) -> None:
    log_detail_bool = LOG_DETAIL == "true"
    console_handler = RichHandler(
        level=CONSOLE_LOG_LEVEL,
        rich_tracebacks=True,
        markup=True,
        show_path=log_detail_bool,
        enable_link_path=True,
        show_level=True,
        show_time=log_detail_bool,
        log_time_format="[%Y-%m-%d %H:%M:%S.%f]",
        tracebacks_show_locals=False,
    )
    logger.addHandler(console_handler)


# Rich traceback handler initialization
install_rich_traceback(show_locals=False)


# --- Logging setup ---
def setup_logging() -> logging.Logger:
    """
    Sets up and returns the application logger.

    Sets up console (RichHandler) and JSON file handlers.
    Returns the existing logger if handlers are already set up.

    Returns:
        The configured logging.Logger instance.
    """
    logger = logging.getLogger(LOGGER_NAME)
    # Prevent duplicate setup if handlers are already configured
    if logger.hasHandlers():
        return logger

    # Set the logger's level to the lower of console and file log levels
    effective_level = min(CONSOLE_LOG_LEVEL, JSON_LOG_LEVEL)
    logger.setLevel(effective_level)

    # Configure console handler
    configure_console_handler(logger)

    # JSON file handler setup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_log_filename = LOG_DIR / JSON_LOG_FILENAME_FORMAT.format(timestamp=timestamp)
    try:
        json_file_handler = logging.FileHandler(json_log_filename, encoding="utf-8")
        json_file_handler.setLevel(JSON_LOG_LEVEL)
        json_formatter = JsonFormatter()
        json_file_handler.setFormatter(json_formatter)
        logger.addHandler(json_file_handler)
    except OSError as e:
        # Log error if file handler creation fails
        logging.error(f"Failed to create log file handler for {json_log_filename}: {e}")

    # Prevent log messages from propagating to the root logger
    logger.propagate = False
    return logger


# --- Logger instance ---
_logger = setup_logging()


def get_logger() -> logging.Logger:
    """
    Returns the configured logger instance.

    Returns:
        The pre-configured logging.Logger instance.
    """
    return _logger
