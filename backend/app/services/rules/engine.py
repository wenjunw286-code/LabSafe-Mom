"""Rule Engine — deterministic evaluation of risk rules.

Evaluates YAML-defined rules against chemical identities, exposure profiles,
and detected lab operations. Produces a list of fired rules with score
contributions — fully deterministic with no LLM involvement.

Same inputs ALWAYS produce same outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import structlog

from app.services.rules.loader import RuleCondition, RuleDefinition, RuleLoader, get_rule_loader

logger = structlog.get_logger(__name__)

# ── Regex cache ────────────────────────────────────────────────────


@lru_cache(maxsize=256)
def _cached_regex_search(pattern: str, value: str) -> bool:
    """Cached regex search to avoid recompiling patterns."""
    try:
        return bool(re.search(pattern, value, re.IGNORECASE))
    except re.error:
        return False


# ── Rule Context ─────────────────────────────────────────────────

@dataclass
class RuleContext:
    """All data available for rule evaluation.

    Bundles chemical identity, exposure profile, detected operations,
    and target population into a single evaluation context.
    """

    # Chemical properties (from ChemicalIdentity)
    chemical: dict[str, Any] = field(default_factory=dict)

    # Exposure inferences (from ExposureAnalyzer)
    exposure: dict[str, Any] = field(default_factory=dict)

    # Detected lab operations (list of operation dicts)
    operations: list[dict[str, Any]] = field(default_factory=list)

    # Target population: "pregnancy", "fertility", "lactation"
    population: str = "pregnancy"

    # All chemicals in the protocol (for cross-substance rules)
    all_chemicals: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RuleResult:
    """A single rule that fired during evaluation."""

    rule_id: str
    rule_name: str
    substance_name: str
    score_contribution: int
    rule_reason: str
    population: str
    category: str
    evidence_note: str | None = None


# ── Condition Evaluator ──────────────────────────────────────────

def _get_value(context: RuleContext, condition: RuleCondition) -> Any:
    """Extract the value to check from the context based on condition type."""
    if condition.type == "field_check":
        return context.chemical.get(condition.field)
    elif condition.type == "exposure_check":
        return context.exposure.get(condition.field)
    elif condition.type == "operation_check":
        # Check across all operations
        for op in context.operations:
            val = op.get(condition.field)
            if val is not None:
                # For boolean checks, return True if any operation matches
                return val
        # For aggregation operators
        if condition.operator == "count_greater_than":
            total = 0
            for op in context.operations:
                routes = op.get(condition.field, [])
                if isinstance(routes, list):
                    total += len(routes)
            return total
        return None
    return None


def _evaluate_condition(context: RuleContext, condition: RuleCondition) -> bool:
    """Recursively evaluate a condition against the context."""
    if condition.type == "compound":
        sub_results = [
            _evaluate_condition(context, sub) for sub in (condition.conditions or [])
        ]
        if condition.operator == "all":
            return all(sub_results)
        elif condition.operator == "any":
            return any(sub_results)
        return False

    # Simple condition
    value = _get_value(context, condition)
    op = condition.operator
    expected = condition.value

    if value is None:
        return False

    try:
        if op == "equals":
            if isinstance(expected, bool):
                return bool(value) == expected
            return str(value).lower() == str(expected).lower()
        elif op == "not_equals":
            return str(value).lower() != str(expected).lower()
        elif op == "in":
            if isinstance(expected, list):
                return str(value) in [str(e) for e in expected]
            return str(value) in str(expected)
        elif op == "contains":
            return str(expected).lower() in str(value).lower()
        elif op == "matches_regex":
            return _cached_regex_search(str(expected), str(value))
        elif op == "less_than":
            try:
                return float(value) < float(expected)
            except (ValueError, TypeError):
                return False
        elif op == "greater_than":
            try:
                return float(value) > float(expected)
            except (ValueError, TypeError):
                return False
        elif op == "is_not_null":
            return value is not None and value != "" and value != []
        elif op == "count_greater_than":
            try:
                return int(value) > int(expected)
            except (ValueError, TypeError):
                return False
    except Exception:
        return False

    return False


# ── Rule Engine ──────────────────────────────────────────────────

class RuleEngine:
    """Deterministic rule evaluation engine.

    Evaluates YAML-defined rules against chemical identity and exposure
    data. All evaluations are pure functions — no network, no randomness,
    no LLM. Results are fully reproducible.

    Usage:
        engine = RuleEngine()
        results = engine.evaluate(chemicals, exposures, population)
        for r in results:
            print(f"{r.rule_id}: {r.rule_reason} = +{r.score_contribution}")
    """

    def __init__(self, loader: RuleLoader | None = None):
        self._loader = loader or get_rule_loader()

    @property
    def rules(self) -> list[RuleDefinition]:
        return self._loader.rules

    def evaluate(
        self,
        chemicals: list[dict[str, Any]],
        exposures: list[dict[str, Any]],
        population: str,
        operations: list[dict[str, Any]] | None = None,
    ) -> list[RuleResult]:
        """Evaluate all rules against all chemicals.

        Args:
            chemicals: List of chemical identity dicts (from ChemicalIdentity.to_dict())
            exposures: List of exposure profile dicts (one per chemical)
            population: "pregnancy", "fertility", or "lactation"
            operations: Detected lab operations from ontology detector

        Returns:
            List of RuleResult for all fired rules, sorted by priority.
        """
        if operations is None:
            operations = []

        all_results: list[RuleResult] = []

        for i, chem in enumerate(chemicals):
            exp = exposures[i] if i < len(exposures) else {}
            ctx = RuleContext(
                chemical=chem,
                exposure=exp,
                operations=operations,
                population=population,
                all_chemicals=chemicals,
            )

            for rule in self._loader.rules:
                try:
                    if (
                        rule.category == "exposure_condition"
                        and _is_low_reproductive_hazard(chem)
                    ):
                        continue
                    if _evaluate_condition(ctx, rule.condition):
                        score = getattr(rule.score_contribution, population, 0)
                        result = RuleResult(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            substance_name=chem.get("canonical_name_en", "Unknown"),
                            score_contribution=score,
                            rule_reason=rule.description,
                            population=population,
                            category=rule.category,
                            evidence_note=rule.evidence_note,
                        )
                        all_results.append(result)
                except Exception as exc:
                    logger.warning(
                        "rule_evaluation_error",
                        rule_id=rule.id,
                        substance=chem.get("canonical_name_en"),
                        error=str(exc),
                    )

        # Sort by priority (highest first) — loader already sorted, but
        # let's ensure consistency
        rule_priority = {r.id: r.priority for r in self._loader.rules}
        all_results.sort(key=lambda r: rule_priority.get(r.rule_id, 0), reverse=True)

        return all_results

    def evaluate_single(
        self,
        chemical: dict[str, Any],
        exposure: dict[str, Any],
        population: str,
        operations: list[dict[str, Any]] | None = None,
    ) -> list[RuleResult]:
        """Evaluate rules for a single chemical.

        Convenience wrapper around evaluate() for single-substance analysis.
        """
        return self.evaluate(
            chemicals=[chemical],
            exposures=[exposure],
            population=population,
            operations=operations,
        )

    def evaluate_all(
        self,
        chemicals: list[dict[str, Any]],
        exposures: list[dict[str, Any]],
        operations: list[dict[str, Any]] | None = None,
    ) -> list[RuleResult]:
        """Evaluate rules once, returning results for ALL three populations.

        This is ~3x faster than calling evaluate() three times because
        condition evaluation (the expensive part) is done once. Only the
        per-population score extraction differs.

        Args:
            chemicals: List of chemical identity dicts
            exposures: List of exposure profile dicts (one per chemical)
            operations: Detected lab operations from ontology detector

        Returns:
            List of RuleResult for all fired rules across all populations.
        """
        if operations is None:
            operations = []

        all_results: list[RuleResult] = []

        for i, chem in enumerate(chemicals):
            exp = exposures[i] if i < len(exposures) else {}
            ctx = RuleContext(
                chemical=chem,
                exposure=exp,
                operations=operations,
                population="pregnancy",  # placeholder — not used in condition eval
                all_chemicals=chemicals,
            )

            for rule in self._loader.rules:
                try:
                    if (
                        rule.category == "exposure_condition"
                        and _is_low_reproductive_hazard(chem)
                    ):
                        continue
                    if _evaluate_condition(ctx, rule.condition):
                        # Rule fired — add results for each population that has a non-zero score
                        sc = rule.score_contribution
                        populations = ["pregnancy", "fertility", "lactation"]
                        for pop in populations:
                            score = getattr(sc, pop, 0)
                            if score != 0:
                                all_results.append(RuleResult(
                                    rule_id=rule.id,
                                    rule_name=rule.name,
                                    substance_name=chem.get("canonical_name_en", "Unknown"),
                                    score_contribution=score,
                                    rule_reason=rule.description,
                                    population=pop,
                                    category=rule.category,
                                    evidence_note=rule.evidence_note,
                                ))
                except Exception as exc:
                    logger.warning(
                        "rule_evaluation_error",
                        rule_id=rule.id,
                        substance=chem.get("canonical_name_en"),
                        error=str(exc),
                    )

        # Sort by priority
        rule_priority = {r.id: r.priority for r in self._loader.rules}
        all_results.sort(key=lambda r: rule_priority.get(r.rule_id, 0), reverse=True)

        return all_results


# ── Module-level convenience ─────────────────────────────────────

_engine: RuleEngine | None = None


def get_rule_engine() -> RuleEngine:
    """Get or create the singleton rule engine."""
    global _engine
    if _engine is None:
        _engine = RuleEngine()
    return _engine


def _is_low_reproductive_hazard(chemical: dict[str, Any]) -> bool:
    """Skip generic exposure add-ons for chemicals classified low or safe."""
    if any(
        chemical.get(field)
        for field in ("reproductive_toxin", "teratogen", "mutagen")
    ):
        return False
    if chemical.get("carcinogen_class") in {"1", "2A", "2B"}:
        return False

    risk_values = [
        str(chemical.get("pregnancy_risk") or "").lower(),
        str(chemical.get("fertility_risk") or "").lower(),
        str(chemical.get("lactation_risk") or "").lower(),
    ]
    if not any(risk_values):
        return False
    return all(
        ("safe" in value or "low" in value or "acceptable" in value)
        for value in risk_values
        if value
    )
