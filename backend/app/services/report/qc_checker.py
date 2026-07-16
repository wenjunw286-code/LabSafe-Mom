"""Quality Control Checker — verifies report integrity before delivery.

Ensures:
1. No chemical missed during normalization
2. Every CAS number matched
3. Every synonym resolved to canonical identity
4. Every risk claim has documented evidence
5. Confidence score calculated

Flags issues rather than blocking — issues are included in the report as
qc_warnings for transparency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class QCResult:
    """Result of quality control verification."""

    passed: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence_score: float = 1.0  # 0.0 to 1.0
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


class QCChecker:
    """Verify report quality before returning to the user.

    Checks are non-blocking — issues are reported as warnings in the
    final report so users can assess report reliability themselves.

    Usage:
        qc = QCChecker()
        result = qc.verify(report_dict, raw_extractions, normalized_chemicals)
        if not result.passed:
            report["qc_warnings"] = result.issues
    """

    # Minimum confidence to pass QC
    MIN_CONFIDENCE = 0.5

    def verify(
        self,
        report: dict[str, Any],
        raw_extractions: list[str],
        normalized_chemicals: list[dict[str, Any]],
        rule_results: list[Any] | None = None,
    ) -> QCResult:
        """Run all QC checks on a generated report.

        Args:
            report: The generated report dict
            raw_extractions: Raw chemical names from extraction pipeline
            normalized_chemicals: Normalized chemical identity dicts
            rule_results: Fired rule results (optional, for rule audit)

        Returns:
            QCResult with pass/fail, issues, and confidence score.
        """
        issues: list[str] = []
        warnings: list[str] = []

        # ── Check 1: No chemical missed in normalization ─────────
        raw_names = set(r.lower().strip() for r in raw_extractions if r)
        normalized_names = set(
            n.get("canonical_name_en", "").lower().strip()
            for n in normalized_chemicals
        )
        normalized_names.update(
            n.get("substance_name", "").lower().strip()
            for n in normalized_chemicals
        )
        normalized_names.discard("")

        missed = raw_names - normalized_names
        if missed:
            issues.append(
                f"{len(missed)} chemical(s) not normalized: {', '.join(sorted(missed))}"
            )

        # ── Check 2: Every CAS number matched ────────────────────
        unmatched_cas = [
            n.get("cas_number")
            for n in normalized_chemicals
            if n.get("cas_number") and not n.get("id")
        ]
        if unmatched_cas:
            warnings.append(
                f"{len(unmatched_cas)} CAS numbers could not be matched: {unmatched_cas}"
            )

        # ── Check 3: Synonym resolution ──────────────────────────
        unresolvable = [
            n.get("canonical_name_en", n.get("substance_name", "?"))
            for n in normalized_chemicals
            if not n.get("id")  # No ChemicalIdentity ID = not resolved
        ]
        if unresolvable:
            issues.append(
                f"{len(unresolvable)} substance(s) could not be resolved to canonical identity: {unresolvable}"
            )

        # ── Check 4: Risk claims have evidence ───────────────────
        substances = report.get("identified_hazardous_materials", [])
        no_reason = [
            s.get("substance_name", "?")
            for s in substances
            if not s.get("risk_reason")
        ]
        if no_reason:
            issues.append(
                f"{len(no_reason)} substance(s) missing risk explanation: {no_reason}"
            )

        # ── Check 5: Rule audit completeness ─────────────────────
        if rule_results is not None and not rule_results:
            warnings.append(
                "No rules fired during assessment — risk scores are zero or default"
            )

        # ── Check 6: Population coverage ─────────────────────────
        for s in substances:
            name = s.get("substance_name", "?")
            for pop in ["pregnancy_risk", "fertility_risk", "lactation_risk"]:
                if not s.get(pop):
                    warnings.append(f"Missing {pop} assessment for {name}")

        # ── Confidence calculation ───────────────────────────────
        total_raw = len(raw_extractions)
        resolved = len(normalized_chemicals) - len(unresolvable)
        confidence = resolved / max(total_raw, 1)

        # Adjust confidence based on issues
        issue_penalty = len(issues) * 0.05
        warning_penalty = len(warnings) * 0.02
        confidence = max(0.0, min(1.0, confidence - issue_penalty - warning_penalty))
        confidence = round(confidence, 2)

        # ── Stats ─────────────────────────────────────────────────
        stats = {
            "raw_extractions_count": len(raw_extractions),
            "normalized_count": len(normalized_chemicals),
            "resolved_count": resolved,
            "unresolvable_count": len(unresolvable),
            "missed_count": len(missed),
            "substances_with_evidence": len(substances) - len(no_reason),
            "total_substances": len(substances),
            "fired_rules": len(rule_results) if rule_results else 0,
        }

        passed = confidence >= self.MIN_CONFIDENCE and len(issues) == 0

        result = QCResult(
            passed=passed,
            issues=issues,
            warnings=warnings,
            confidence_score=confidence,
            stats=stats,
        )

        if not passed:
            logger.warning(
                "qc_failed",
                issues=issues,
                warnings=warnings,
                confidence=confidence,
            )
        else:
            logger.info(
                "qc_passed",
                confidence=confidence,
                stats=stats,
            )

        return result
