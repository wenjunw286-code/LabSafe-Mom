"""Prompt template loader.

Loads prompt templates from YAML files, validates with Pydantic,
and provides type-safe `.format(**kwargs)` for runtime substitution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent


class PromptTemplate(BaseModel):
    """A single prompt template with system and user messages."""

    name: str = Field(..., description="Template identifier")
    description: str = Field(default="", description="What this prompt is used for")
    version: str = Field(default="1.0")
    system: str = Field(..., description="System prompt")
    user: str = Field(..., description="User prompt template with {placeholders}")

    @field_validator("system", "user")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Prompt text cannot be empty")
        return v

    def format(self, **kwargs: Any) -> dict[str, str]:
        """Format the prompt with provided keyword arguments.

        Returns:
            Dict with 'system' and 'user' keys, ready for OpenAI API.
        """
        return {
            "system": self.system,
            "user": self.user.format(**kwargs),
        }


class PromptLoader:
    """Load and cache prompt templates from YAML files."""

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self._dir = prompts_dir or _PROMPTS_DIR
        self._cache: dict[str, PromptTemplate] = {}

    def load(self, name: str) -> PromptTemplate:
        """Load a prompt template by name (without .yaml extension).

        Caches the loaded template in memory.
        """
        if name in self._cache:
            return self._cache[name]

        file_path = self._dir / f"{name}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        template = PromptTemplate(**raw)
        self._cache[name] = template
        logger.debug("prompt_loaded", name=name, version=template.version)
        return template

    def reload(self, name: str) -> PromptTemplate:
        """Force reload a prompt template, bypassing the cache."""
        self._cache.pop(name, None)
        return self.load(name)


# ── Global singleton ──────────────────────────────────────────
prompt_loader = PromptLoader()
