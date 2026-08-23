"""Application configuration loaded from environment variables.

Uses pydantic-settings for validation and .env file support.
All settings have sensible defaults for development.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """OpenAI-compatible API settings."""

    model_config = SettingsConfigDict(env_prefix="AI_", extra="ignore")

    model: str = Field(default="deepseek-v4-pro", description="LLM model name")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens_extraction: int = Field(default=4000, ge=1)
    max_tokens_assessment: int = Field(default=1500, ge=1)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_min_wait: float = Field(default=1.0, ge=0.1, description="Min seconds between retries")
    retry_max_wait: float = Field(default=30.0, ge=1.0)
    retry_backoff: float = Field(default=2.0, ge=1.0, description="Exponential backoff multiplier")
    request_timeout: float = Field(default=30.0, ge=5.0, description="Timeout per AI request in seconds")


class CacheSettings(BaseSettings):
    """AI response cache settings."""

    model_config = SettingsConfigDict(env_prefix="CACHE_", extra="ignore")

    ttl_seconds: int = Field(default=3600, ge=60, description="Cache TTL for AI responses")
    max_size: int = Field(default=1000, ge=1, description="Max cache entries")
    enabled: bool = Field(default=True)


class RateLimitSettings(BaseSettings):
    """API rate limiting settings."""

    model_config = SettingsConfigDict(env_prefix="RATE_LIMIT_", extra="ignore")

    requests_per_minute: int = Field(default=30, ge=1)
    burst_size: int = Field(default=5, ge=1)
    enabled: bool = Field(default=True)


class CORSSettings(BaseSettings):
    """CORS configuration."""

    model_config = SettingsConfigDict(env_prefix="CORS_", extra="ignore")

    origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins (comma-separated or JSON list in env)",
    )
    allow_credentials: bool = True
    allow_methods: list[str] = Field(default=["*"])
    allow_headers: list[str] = Field(default=["*"])

    @field_validator("origins", "allow_methods", "allow_headers", mode="before")
    @classmethod
    def _parse_env_list(cls, value):
        """Accept JSON arrays or comma-separated strings in hosting dashboards."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value


class Settings(BaseSettings):
    """Root application settings loaded from .env file and environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        # Allow lists to be parsed from JSON or comma-separated strings
    )

    # ── Database ──────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite+aiosqlite:///./labsafe.db",
        description="Async database URL (use sqlite+aiosqlite:// or postgresql+asyncpg://)",
    )
    database_url_sync: str = Field(
        default="",
        description="Sync database URL for seed data; defaults to database_url with sync driver",
    )

    # ── OpenAI / LLM ──────────────────────────────────────────
    openai_api_key: str = Field(default="", repr=False)
    openai_base_url: str = Field(default="")
    ai: AISettings = Field(default_factory=AISettings)

    # ── File Upload ───────────────────────────────────────────
    max_file_size_mb: int = Field(default=50, ge=1, le=500)
    upload_dir: str = Field(default="./uploads")
    allowed_extensions: list[str] = Field(default=["pdf", "docx", "txt"])
    verify_mime_type: bool = Field(default=False, description="Verify MIME type with python-magic (disabled due to Python 3.13 compat)")

    # ── Infrastructure ────────────────────────────────────────
    cors: CORSSettings = Field(default_factory=CORSSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)

    # ── Logging ───────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    log_format: Literal["console", "json"] = Field(default="console")
    log_redact_sensitive: bool = Field(default=True)

    # ── Application ───────────────────────────────────────────
    app_name: str = Field(default="LabSafe Mom API")
    app_version: str = Field(default="2.0.0")
    debug: bool = Field(default=False)
    environment: Literal["development", "staging", "production"] = Field(default="development")

    @model_validator(mode="after")
    def _fix_database_urls(self) -> "Settings":
        """Ensure database_url is async and database_url_sync is sync.

        If the user provides a sync-only URL (e.g., sqlite:///...),
        automatically convert it to the async equivalent.
        """
        # Convert sync URL → async URL if needed
        if "+aiosqlite" not in self.database_url and "+asyncpg" not in self.database_url:
            if self.database_url.startswith("sqlite://"):
                self.database_url = self.database_url.replace("sqlite://", "sqlite+aiosqlite://")
            elif self.database_url.startswith("postgresql://"):
                self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://")

        # Derive sync URL from async URL
        if not self.database_url_sync:
            self.database_url_sync = (
                self.database_url
                .replace("+aiosqlite", "")
                .replace("+asyncpg", "")
                .replace("postgresql+asyncpg", "postgresql")
                .replace("sqlite+aiosqlite", "sqlite")
            )
        return self

    @property
    def max_file_size_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """Whether running in production mode."""
        return self.environment == "production"


# ── Global singleton ──────────────────────────────────────────
def _normalize_list_env(name: str) -> None:
    """Convert comma-separated dashboard values to JSON arrays before settings load."""
    value = os.environ.get(name)
    if not value:
        return

    stripped = value.strip()
    if stripped.startswith("["):
        return

    os.environ[name] = json.dumps(
        [item.strip() for item in stripped.split(",") if item.strip()]
    )


for _env_name in ("CORS_ORIGINS", "CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS"):
    _normalize_list_env(_env_name)


settings = Settings()
