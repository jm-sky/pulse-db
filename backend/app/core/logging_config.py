"""Logging configuration for the application."""

import logging
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings


def configure_logging() -> None:
    """
    Configure application logging.

    Sets up logging based on environment and configuration.
    Should be called before creating the FastAPI app.
    """
    # Determine log level
    log_level = getattr(logging, settings.logging.level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(fmt=settings.logging.format, datefmt="%Y-%m-%d %H:%M:%S")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if log file is specified
    if settings.logging.file:
        log_path = Path(settings.logging.file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers in production
    if settings.is_production():
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    else:
        # In development, show SQL queries if database_echo is True
        if settings.database.echo:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    logging.info(f"Logging configured: level={settings.logging.level}, environment={settings.app.environment}")


class ServiceLogger:
    """
    Wrapper for logging with consistent formatting and context.

    Example:
        logger = ServiceLogger("auth_service")
        logger.info("User logged in", user_id="123", email="user@example.com")
    """

    def __init__(self, name: str):
        """Initialize logger with name."""
        self.logger = logging.getLogger(name)
        self.name = name

    def _format_message(self, message: str, **context: Any) -> str:
        """Format message with context."""
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            return f"{message} | {context_str}"
        return message

    def debug(self, message: str, **context: Any) -> None:
        """Log debug message."""
        self.logger.debug(self._format_message(message, **context))

    def info(self, message: str, **context: Any) -> None:
        """Log info message."""
        self.logger.info(self._format_message(message, **context))

    def warning(self, message: str, **context: Any) -> None:
        """Log warning message."""
        self.logger.warning(self._format_message(message, **context))

    def error(self, message: str, **context: Any) -> None:
        """Log error message."""
        self.logger.error(self._format_message(message, **context))

    def critical(self, message: str, **context: Any) -> None:
        """Log critical message."""
        self.logger.critical(self._format_message(message, **context))

    def exception(self, message: str, **context: Any) -> None:
        """Log exception with traceback."""
        self.logger.exception(self._format_message(message, **context))
