"""
Logging Configuration
Sets up structured JSON logging for the utility meter system
"""
import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_obj.update(record.extra_fields)

        return json.dumps(log_obj)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for console output"""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Set up logging based on configuration

    Args:
        config: Logging configuration dict with keys:
            - level: Logging level (DEBUG, INFO, WARNING, ERROR)
            - format: Output format (json or text)
            - file: Log file path (optional)
            - max_bytes: Max file size before rotation (default: 10MB)
            - backup_count: Number of backup files to keep (default: 5)
    """
    log_config = config.get("logging", {})
    level_str = log_config.get("level", "INFO").upper()
    log_format = log_config.get("format", "json").lower()
    log_file = log_config.get("file")
    max_bytes = log_config.get("max_bytes", 10485760)  # 10 MB default
    backup_count = log_config.get("backup_count", 5)

    # Map string level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    level = level_map.get(level_str, logging.INFO)

    # Choose formatter
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers = []

    # Add console handler (always present)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if log file specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    root_logger.info(
        f"Logging configured: level={level_str}, format={log_format}, "
        f"file={'enabled' if log_file else 'disabled'}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: int, message: str, **context):
    """
    Log a message with additional context fields (for JSON logging)

    Args:
        logger: Logger instance
        level: Logging level (logging.INFO, logging.WARNING, etc.)
        message: Log message
        **context: Additional key-value pairs to include in JSON output
    """
    extra_record = logging.LogRecord(
        name=logger.name,
        level=level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    extra_record.extra_fields = context
    logger.handle(extra_record)
