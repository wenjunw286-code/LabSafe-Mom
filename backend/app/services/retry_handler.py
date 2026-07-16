"""Centralized retry configuration for external API calls.

Uses tenacity for exponential backoff with jitter on all LLM interactions.
Handles common transient failures: rate limits, network timeouts, 5xx errors.
"""

from __future__ import annotations

import structlog
from openai import (
    APIError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
    APIConnectionError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)

from app.config import settings

logger = structlog.get_logger(__name__)

# Transient errors that should trigger a retry
_RETRYABLE_EXCEPTIONS = (
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,  # 5xx
)

_ai_config = settings.ai


def make_ai_retry(attempts: int | None = None, min_wait: float | None = None):
    """Create a tenacity retry decorator configured for AI API calls.

    Args:
        attempts: Max retry attempts (defaults to config).
        min_wait: Minimum wait in seconds (defaults to config).

    Returns:
        A tenacity retry decorator.
    """
    return retry(
        stop=stop_after_attempt(attempts or _ai_config.max_retries),
        wait=wait_exponential(
            multiplier=(min_wait or _ai_config.retry_min_wait),
            min=(min_wait or _ai_config.retry_min_wait),
            max=_ai_config.retry_max_wait,
        ),
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, "WARNING"),
        after=after_log(logger, "DEBUG"),
        reraise=True,
    )


# Common predefined retry decorators
ai_retry = make_ai_retry()
ai_retry_quick = make_ai_retry(attempts=2, min_wait=0.5)  # For non-critical calls
