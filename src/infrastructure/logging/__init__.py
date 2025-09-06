"""Logging infrastructure initialization."""

import logging
import sys
from pathlib import Path

import structlog

# Optional import for JSON logging
try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False
    jsonlogger = None

from ..config.settings import get_settings


def setup_logging():
    """Set up structured logging for the application."""
    settings = get_settings()

    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, settings.logging.level.upper()),
        format=settings.logging.format,
        stream=sys.stdout,
    )

    # Configure structlog
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Console logging
    if settings.logging.console.enabled:
        console_processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

        structlog.configure(
            processors=console_processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    # File logging
    if settings.logging.file.enabled:
        log_path = Path(settings.logging.file.path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_processors = shared_processors + [
            structlog.processors.JSONRenderer(),
        ]

        # Set up file handler
        file_handler = logging.FileHandler(
            settings.logging.file.path,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, settings.logging.level.upper()))

        # JSON formatter for file
        if HAS_JSON_LOGGER and jsonlogger:
            formatter = jsonlogger.JsonFormatter(
                fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
            )
            file_handler.setFormatter(formatter)
        else:
            # Fallback to basic formatter
            formatter = logging.Formatter(
                fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
            )
            file_handler.setFormatter(formatter)

        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

    # Set up loggers for specific modules
    _setup_module_loggers()


def _setup_module_loggers():
    """Set up specific loggers for different modules."""
    # Database logger
    db_logger = logging.getLogger('duckdb_financial.database')
    db_logger.setLevel(logging.INFO)

    # Scanner logger
    scanner_logger = logging.getLogger('duckdb_financial.scanner')
    scanner_logger.setLevel(logging.INFO)

    # Broker logger
    broker_logger = logging.getLogger('duckdb_financial.broker')
    broker_logger.setLevel(logging.INFO)

    # API logger
    api_logger = logging.getLogger('duckdb_financial.api')
    api_logger.setLevel(logging.INFO)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger for the given name."""
    return structlog.get_logger(name)


# Initialize logging on import
# setup_logging()
