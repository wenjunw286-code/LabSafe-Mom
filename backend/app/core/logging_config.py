"""Structured logging configuration using structlog.

Provides JSON logging for production and pretty console output for development.
Redacts sensitive values (API keys, tokens) from log output.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from typing import Any

import structlog

from app.config import settings

# Sensitive key patterns to redact in log output
_SENSITIVE_KEY_PATTERNS = re.compile(
    r"(api_key|apikey|secret|password|token|authorization|credential)",
    re.IGNORECASE,
)
_SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie", "set-cookie"}


def _redact_sensitive(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive values from log event dictionaries."""
    if not settings.log_redact_sensitive:
        return event_dict

    redacted: dict[str, Any] = {}
    for key, value in event_dict.items():
        if isinstance(value, str) and len(value) > 20 and _SENSITIVE_KEY_PATTERNS.match(key):
            redacted[key] = value[:4] + "****" + value[-4:] if value else ""
        elif key in _SENSITIVE_HEADERS:
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted


def _add_app_context(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add application metadata to every log entry."""
    event_dict.setdefault("app", settings.app_name)
    event_dict.setdefault("env", settings.environment)
    event_dict.setdefault("version", settings.app_version)
    return event_dict


def setup_logging() -> None:
    """Configure structlog with renderers based on environment.

    Should be called once at application startup.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _add_app_context,
    ]

    if settings.log_format == "json":
        # Production: JSON to stdout
        structlog.configure(
            processors=shared_processors
            + [
                structlog.processors.format_exc_info,
                _redact_sensitive,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Development: pretty console output
        # NOTE: format_exc_info removed — ConsoleRenderer handles exceptions natively
        structlog.configure(
            processors=shared_processors
            + [
                _redact_sensitive,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Set the root logger level
    logging.getLogger().setLevel(getattr(logging, settings.log_level))

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Log startup
    logger = structlog.get_logger(__name__)
    logger.info(
        "logging_initialized",
        format=settings.log_format,
        level=settings.log_level,
    )
