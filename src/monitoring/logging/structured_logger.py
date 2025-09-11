"""
Advanced Structured Logging Framework
====================================

This module provides a sophisticated logging system with:
- Structured JSON logging
- Correlation ID tracking
- Log aggregation and filtering
- Multiple output handlers
- Performance monitoring
"""

import logging
import logging.handlers
import json
import sys
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
from contextvars import ContextVar
import uuid
import inspect
import os
import threading
from dataclasses import dataclass, asdict

from ..config.settings import config
from ..config.database import monitoring_db


# Context variable for correlation ID
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


@dataclass
class LogEntry:
    """Structured log entry data class."""
    timestamp: datetime
    level: str
    component: str
    message: str
    extra_data: Dict[str, Any]
    correlation_id: Optional[str]
    source_file: Optional[str]
    source_line: Optional[int]
    function_name: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'component': self.component,
            'message': self.message,
            'extra_data': self.extra_data,
            'correlation_id': self.correlation_id,
            'source_file': self.source_file,
            'source_line': self.source_line,
            'function_name': self.function_name
        }


class StructuredJSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Get correlation ID from context
        correlation_id = correlation_id_context.get()

        # Extract caller information
        frame = inspect.currentframe()
        try:
            # Go up the stack to find the actual caller
            caller_frame = frame.f_back.f_back.f_back
            if caller_frame:
                source_file = caller_frame.f_code.co_filename
                source_line = caller_frame.f_lineno
                function_name = caller_frame.f_code.co_name
            else:
                source_file = record.filename
                source_line = record.lineno
                function_name = record.funcName
        finally:
            del frame

        # Extract extra data from record
        extra_data = {}
        if hasattr(record, '__dict__'):
            # Get data passed via the 'extra' parameter
            reserved_keys = {'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                           'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                           'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                           'thread', 'threadName', 'processName', 'process', 'message'}

            for key, value in record.__dict__.items():
                if key not in reserved_keys:
                    extra_data[key] = value

        # Create log entry
        log_entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created),
            level=record.levelname,
            component=record.name,
            message=record.getMessage(),
            extra_data=extra_data,
            correlation_id=correlation_id,
            source_file=source_file,
            source_line=source_line,
            function_name=function_name
        )

        return json.dumps(log_entry.to_dict(), default=str, ensure_ascii=False)


class MonitoringHandler(logging.Handler):
    """Custom handler that stores logs in the monitoring database."""

    def __init__(self, level: int = logging.DEBUG):
        super().__init__(level)
        self._buffer: List[LogEntry] = []
        self._buffer_size = 50  # Batch size for database inserts
        self._flush_interval = 5  # Seconds between flushes
        self._last_flush = datetime.now()
        self._lock = threading.Lock()

        # Start background flush thread
        self._stop_event = threading.Event()
        self._flush_thread = threading.Thread(target=self._background_flush, daemon=True)
        self._flush_thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        """Process log record and add to buffer."""
        try:
            # Get correlation ID from context
            correlation_id = correlation_id_context.get()

            # Extract caller information
            frame = inspect.currentframe()
            try:
                caller_frame = frame.f_back.f_back.f_back
                if caller_frame:
                    source_file = caller_frame.f_code.co_filename
                    source_line = caller_frame.f_lineno
                    function_name = caller_frame.f_code.co_name
                else:
                    source_file = record.filename
                    source_line = record.lineno
                    function_name = record.funcName
            finally:
                del frame

            # Extract extra data
            extra_data = {}
            if hasattr(record, '__dict__'):
                # Get data passed via the 'extra' parameter
                reserved_keys = {'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                               'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                               'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                               'thread', 'threadName', 'processName', 'process', 'message'}

                for key, value in record.__dict__.items():
                    if key not in reserved_keys:
                        extra_data[key] = value

            # Create log entry
            log_entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created),
                level=record.levelname,
                component=record.name,
                message=record.getMessage(),
                extra_data=extra_data,
                correlation_id=correlation_id,
                source_file=source_file,
                source_line=source_line,
                function_name=function_name
            )

            # Add to buffer
            with self._lock:
                self._buffer.append(log_entry)

                # Check if we should flush
                if (len(self._buffer) >= self._buffer_size or
                    (datetime.now() - self._last_flush).seconds >= self._flush_interval):
                    self._flush_buffer()

        except Exception:
            # Don't let logging errors break the application
            pass

    def _flush_buffer(self) -> None:
        """Flush buffered log entries to database."""
        with self._lock:
            if not self._buffer:
                return

            try:
                with monitoring_db.get_connection() as conn:
                    # Prepare batch insert
                    values = []
                    for entry in self._buffer:
                        values.append((
                            entry.timestamp,
                            entry.level,
                            entry.component,
                            entry.message,
                            json.dumps(entry.extra_data, default=str),
                            entry.correlation_id,
                            entry.source_file,
                            entry.source_line,
                            entry.function_name
                        ))

                    # Execute batch insert
                    conn.executemany("""
                        INSERT INTO system_logs (
                            timestamp, level, component, message, extra_data,
                            correlation_id, source_file, source_line, function_name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, values)

                # Clear buffer
                self._buffer.clear()
                self._last_flush = datetime.now()

            except Exception:
                # If database insert fails, keep buffer for retry
                pass

    def _background_flush(self) -> None:
        """Background thread for periodic buffer flushing."""
        while not self._stop_event.is_set():
            self._stop_event.wait(self._flush_interval)
            if not self._stop_event.is_set():
                self._flush_buffer()

    def close(self) -> None:
        """Clean up handler resources."""
        self._stop_event.set()
        self._flush_thread.join()
        self._flush_buffer()  # Final flush
        super().close()


class StructuredLogger:
    """Main structured logging class."""

    _loggers: Dict[str, logging.Logger] = {}
    _configured = False

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create a structured logger."""
        if not cls._configured:
            cls._configure_logging()

        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def _configure_logging(cls) -> None:
        """Configure the logging system."""
        if cls._configured:
            return

        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Set root logger level
        root_logger.setLevel(logging.DEBUG)

        # Create formatters
        if config.logging.enable_structured_logging:
            formatter = StructuredJSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.logging.console_level))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # File handler (if log directory is configured)
        if config.logging.log_directory:
            log_dir = Path(config.logging.log_directory)
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_dir / "monitoring.log",
                maxBytes=cls._parse_size(config.logging.max_log_size),
                backupCount=config.logging.backup_count
            )
            file_handler.setLevel(getattr(logging, config.logging.file_level))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        # Monitoring database handler
        if config.enable_monitoring:
            monitoring_handler = MonitoringHandler()
            monitoring_handler.setLevel(logging.DEBUG)
            root_logger.addHandler(monitoring_handler)

        cls._configured = True

    @staticmethod
    def _parse_size(size_str: str) -> int:
        """Parse size string like '10 MB' to bytes."""
        size_str = size_str.upper().strip()
        if size_str.endswith('GB'):
            return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
        elif size_str.endswith('MB'):
            return int(float(size_str[:-2]) * 1024 * 1024)
        elif size_str.endswith('KB'):
            return int(float(size_str[:-2]) * 1024)
        else:
            return int(size_str)

    @staticmethod
    def set_correlation_id(correlation_id: Optional[str] = None) -> str:
        """Set correlation ID for current context."""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        correlation_id_context.set(correlation_id)
        return correlation_id

    @staticmethod
    def get_correlation_id() -> Optional[str]:
        """Get current correlation ID."""
        return correlation_id_context.get()


# Convenience functions
def get_logger(name: str) -> logging.Logger:
    """Get a structured logger instance."""
    return StructuredLogger.get_logger(name)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID for current context."""
    return StructuredLogger.set_correlation_id(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return StructuredLogger.get_correlation_id()
