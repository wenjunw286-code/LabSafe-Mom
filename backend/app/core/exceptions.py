"""Custom exception hierarchy for LabSafe Mom.

Provides typed, catchable exceptions with structured error details
for consistent API error responses and logging.
"""

from typing import Any


class LabSafeBaseError(Exception):
    """Base exception for all LabSafe Mom errors."""

    def __init__(self, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "detail": self.detail,
        }


class FileValidationError(LabSafeBaseError):
    """Raised when an uploaded file fails validation (type, size, MIME)."""


class FileParsingError(LabSafeBaseError):
    """Raised when file content cannot be parsed to text."""


class AIExtractionError(LabSafeBaseError):
    """Raised when the AI chemical extraction fails after all retries."""


class RiskMatchingError(LabSafeBaseError):
    """Raised when risk matching fails for a substance."""


class ReportNotFoundError(LabSafeBaseError):
    """Raised when a requested report does not exist."""


class ReportNotReadyError(LabSafeBaseError):
    """Raised when a report is accessed before analysis is complete."""


class RateLimitExceededError(LabSafeBaseError):
    """Raised when the client exceeds the configured rate limit."""


class AIServiceUnavailableError(LabSafeBaseError):
    """Raised when the AI service (OpenAI) is unavailable or returns 5xx."""


class ConfigurationError(LabSafeBaseError):
    """Raised when the application is misconfigured (e.g., missing API key)."""


class SubstanceNotFoundError(LabSafeBaseError):
    """Raised when a substance is not found in the local database."""
