"""Score Calculator — deterministic risk score computation.

Translates fired rule results into 0-100 risk scores per chemical
per population. Fully deterministic — no LLM, no randomness.

Scoring logic:
  Base score = sum of all fired rule contributions
  Final score = clamp(base_score, 0, 100)

Risk level thresholds:
  >= 75 → Critical
  >= 50 → High
  >= 25 → Moderate
  <  25 → Low
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.rules.engine import RuleResult


# ── Data Models ──────────────────────────────────────────────────

@dataclass
class ChemicalScore:
    """Risk score for one chemical across all populations."""

    substance_name: str
    cas_number: str | None = None
    canonical_name_en: str | None = None
    category: str | None = None

    # Raw scores per population (sum of rule contributions, clamped 0-100)
    pregnancy_score: int = 0
    fertility_score: int = 0
    lactation_score: int = 0

    # Risk levels per population
    pregnancy_risk: str = "Low"
    fertility_risk: str = "Low"
    lactation_risk: str = "Low"

    # Fired rules for this chemical
    fired_rules: list[RuleResult] = field(default_factory=list)

    # Evidence citations collected from fired rules
    evidence_notes: list[str] = field(default_factory=list)


@dataclass
class OverallScore:
    """Aggregate risk score for the entire protocol."""

    # Overall score (maximum per-substance score, clamped 0-100)
    overall_score: int = 0
    overall_risk: str = "Low"  # Critical / High / Moderate / Low

    # Per-substance breakdown
    chemical_scores: list[ChemicalScore] = field(default_factory=list)

    # Population-specific aggregations
    pregnancy_max_score: int = 0
    fertility_max_score: int = 0
    lactation_max_score: int = 0

    # Counts
    total_substances: int = 0
    high_risk_count: int = 0  # Substances with any population at High Risk or Critical
    critical_count: int = 0

    # All fired rules (for audit trail)
    all_fired_rules: list[RuleResult] = field(default_factory=list)


# ── Score Calculator ─────────────────────────────────────────────

class ScoreCalculator:
    """Deterministic risk score calculator.

    Takes rule engine output and produces final 0-100 scores
    per chemical per population. All computation is pure —
    no I/O, no randomness, no LLM.
    """

    # Score → Risk Level mapping thresholds
    CRITICAL_THRESHOLD = 75
    HIGH_THRESHOLD = 50
    MODERATE_THRESHOLD = 25

    # Score caps
    MAX_SCORE = 100
    MIN_SCORE = 0

    @staticmethod
    def score_to_risk_level(score: int) -> str:
        """Convert a numeric score (0-100) to a risk level label."""
        if score >= ScoreCalculator.CRITICAL_THRESHOLD:
            return "Critical"
        elif score >= ScoreCalculator.HIGH_THRESHOLD:
            return "High"
        elif score >= ScoreCalculator.MODERATE_THRESHOLD:
            return "Moderate"
        return "Low"

    def calculate(
        self,
        rule_results: list[RuleResult],
        chemicals: list[dict[str, Any]],
        population: str = "pregnancy",
    ) -> OverallScore:
        """Calculate scores from rule evaluation results.

        Args:
            rule_results: All fired rules from RuleEngine.evaluate()
            chemicals: Original chemical identity dicts
            population: Primary population for the assessment

        Returns:
            OverallScore with per-chemical and aggregate scores.
        """
        # Group rules by substance
        by_substance: dict[str, list[RuleResult]] = {}
        for rr in rule_results:
            name = rr.substance_name
            by_substance.setdefault(name, []).append(rr)

        chemical_scores: list[ChemicalScore] = []

        for chem in chemicals:
            name = chem.get("canonical_name_en", "") or chem.get("substance_name", "Unknown")
            rules = by_substance.get(name, [])

            # Sum contributions per population
            preg_sum = sum(
                r.score_contribution for r in rules if r.population == "pregnancy"
            )
            fert_sum = sum(
                r.score_contribution for r in rules if r.population == "fertility"
            )
            lact_sum = sum(
                r.score_contribution for r in rules if r.population == "lactation"
            )

            # Also add contributions from rules that target "all" populations
            # (these are flagged with population matching the assessment population)
            # Actually, each rule result has a population field set by the engine.
            # The engine evaluates rules separately per population when called
            # via evaluate_all_populations(). For single-population calls,
            # only rules with scores for that population fire.
            #
            # For now, aggregate within each population.
            all_rules_for_chem = rules

            # Clamp
            preg_score = max(self.MIN_SCORE, min(self.MAX_SCORE, preg_sum))
            fert_score = max(self.MIN_SCORE, min(self.MAX_SCORE, fert_sum))
            lact_score = max(self.MIN_SCORE, min(self.MAX_SCORE, lact_sum))

            cs = ChemicalScore(
                substance_name=name,
                cas_number=chem.get("cas_number"),
                canonical_name_en=chem.get("canonical_name_en"),
                category=chem.get("category"),
                pregnancy_score=preg_score,
                fertility_score=fert_score,
                lactation_score=lact_score,
                pregnancy_risk=self.score_to_risk_level(preg_score),
                fertility_risk=self.score_to_risk_level(fert_score),
                lactation_risk=self.score_to_risk_level(lact_score),
                fired_rules=all_rules_for_chem,
                evidence_notes=[
                    r.evidence_note
                    for r in all_rules_for_chem
                    if r.evidence_note
                ],
            )
            chemical_scores.append(cs)

        # Aggregate overall score
        if chemical_scores:
            max_scores = []
            for cs in chemical_scores:
                max_scores.append(
                    max(cs.pregnancy_score, cs.fertility_score, cs.lactation_score)
                )
            overall = max(max_scores) if max_scores else 0
            overall = max(self.MIN_SCORE, min(self.MAX_SCORE, overall))
        else:
            overall = 0

        # Count high-risk substances
        high_risk_count = 0
        critical_count = 0
        for cs in chemical_scores:
            risks = [cs.pregnancy_risk, cs.fertility_risk, cs.lactation_risk]
            if "Critical" in risks or "High" in risks:
                high_risk_count += 1
            if "Critical" in risks:
                critical_count += 1

        # Population max scores
        preg_max = max((cs.pregnancy_score for cs in chemical_scores), default=0)
        fert_max = max((cs.fertility_score for cs in chemical_scores), default=0)
        lact_max = max((cs.lactation_score for cs in chemical_scores), default=0)

        return OverallScore(
            overall_score=overall,
            overall_risk=self.score_to_risk_level(overall),
            chemical_scores=chemical_scores,
            pregnancy_max_score=preg_max,
            fertility_max_score=fert_max,
            lactation_max_score=lact_max,
            total_substances=len(chemical_scores),
            high_risk_count=high_risk_count,
            critical_count=critical_count,
            all_fired_rules=rule_results,
        )

    def evaluate_all_populations(
        self,
        engine: Any,  # RuleEngine (avoid circular import)
        chemicals: list[dict[str, Any]],
        exposures: list[dict[str, Any]],
        operations: list[dict[str, Any]] | None = None,
    ) -> OverallScore:
        """Evaluate rules for all three populations and produce combined scores.

        This is the main entry point — it runs the rule engine for
        pregnancy, fertility, and lactation populations, then merges
        results into per-chemical scores.
        """
        all_results: list[RuleResult] = []
        for pop in ["pregnancy", "fertility", "lactation"]:
            results = engine.evaluate(
                chemicals=chemicals,
                exposures=exposures,
                population=pop,
                operations=operations,
            )
            all_results.extend(results)

        # Calculate scores from combined results
        # Use "pregnancy" as the primary population for the OverallScore
        return self.calculate(
            rule_results=all_results,
            chemicals=chemicals,
            population="pregnancy",
        )


# Module-level singleton
_calculator: ScoreCalculator | None = None


def get_score_calculator() -> ScoreCalculator:
    global _calculator
    if _calculator is None:
        _calculator = ScoreCalculator()
    return _calculator
