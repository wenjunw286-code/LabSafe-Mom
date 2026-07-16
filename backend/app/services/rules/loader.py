"""Rule loader — loads and validates YAML rule definitions.

Rules are loaded once at service startup and cached in memory.
All rule definitions are validated with Pydantic for correctness.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger(__name__)


# ── Pydantic Rule Schemas ────────────────────────────────────────

class RuleCondition(BaseModel):
    """A single condition within a rule."""

    type: str  # "field_check", "exposure_check", "operation_check", "compound"
    field: str | None = None
    operator: str = "equals"  # equals, not_equals, in, contains, matches_regex, less_than, greater_than, is_not_null, count_greater_than
    value: Any = None
    conditions: list["RuleCondition"] | None = None  # For compound conditions


class ScoreContribution(BaseModel):
    """Score contribution per population group."""

    pregnancy: int = 0
    fertility: int = 0
    lactation: int = 0


class RuleDefinition(BaseModel):
    """A single rule definition from YAML."""

    id: str  # e.g., "R001"
    name: str  # e.g., "known_reproductive_toxin"
    description: str
    priority: int = 0
    category: str = "general"
    condition: RuleCondition
    score_contribution: ScoreContribution
    evidence_note: str | None = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v.startswith("R") or not v[1:].isdigit():
            raise ValueError(f"Rule ID must be R + number, got: {v}")
        return v


class RulesDocument(BaseModel):
    """Top-level YAML document containing all rules."""

    version: str
    rules: list[RuleDefinition]


# ── Loader ───────────────────────────────────────────────────────

class RuleLoader:
    """Load, validate, and index rule definitions from YAML.

    Rules are sorted by priority (descending) on load.
    Provides lookup by ID and by category.
    """

    def __init__(self, rules_path: str | None = None):
        if rules_path is None:
            rules_path = str(Path(__file__).parent / "rules.yaml")
        self._path = Path(rules_path)
        self._rules: list[RuleDefinition] = []
        self._by_id: dict[str, RuleDefinition] = {}
        self._by_category: dict[str, list[RuleDefinition]] = {}
        self._loaded = False

    @property
    def rules(self) -> list[RuleDefinition]:
        """All rules sorted by priority (highest first)."""
        if not self._loaded:
            self.load()
        return self._rules

    @property
    def rule_count(self) -> int:
        return len(self.rules)

    def get(self, rule_id: str) -> RuleDefinition | None:
        """Get a rule by ID."""
        if not self._loaded:
            self.load()
        return self._by_id.get(rule_id)

    def get_by_category(self, category: str) -> list[RuleDefinition]:
        """Get all rules in a category."""
        if not self._loaded:
            self.load()
        return self._by_category.get(category, [])

    def load(self) -> list[RuleDefinition]:
        """Load and validate rules from YAML file."""
        if not self._path.exists():
            logger.warning("rules_file_not_found", path=str(self._path))
            self._loaded = True
            return []

        raw_text = self._path.read_text(encoding="utf-8")
        raw = yaml.safe_load(raw_text)
        doc = RulesDocument.model_validate(raw)

        # Sort by priority descending
        self._rules = sorted(doc.rules, key=lambda r: r.priority, reverse=True)
        self._by_id = {r.id: r for r in self._rules}
        self._by_category = {}
        for r in self._rules:
            self._by_category.setdefault(r.category, []).append(r)
        self._loaded = True

        logger.info(
            "rules_loaded",
            count=len(self._rules),
            categories=list(self._by_category.keys()),
            path=str(self._path),
        )
        return self._rules

    def reload(self) -> list[RuleDefinition]:
        """Force reload rules from disk (useful for hot-reload in dev)."""
        self._loaded = False
        self._rules = []
        self._by_id = {}
        self._by_category = {}
        return self.load()


# Module-level singleton
_loader: RuleLoader | None = None


def get_rule_loader() -> RuleLoader:
    """Get or create the singleton rule loader."""
    global _loader
    if _loader is None:
        _loader = RuleLoader()
        _loader.load()
    return _loader
