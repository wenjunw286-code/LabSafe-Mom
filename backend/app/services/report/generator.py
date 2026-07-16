"""Report Generator v3 — deterministic report assembly.

Assembles the final report from:
- Rule engine scores (deterministic)
- Evidence citations (from knowledge base)
- Exposure analysis results
- Detected lab operations
- LLM-generated summary text (natural language only)

Does NOT compute any risk scores — those come from the rule engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from app.services.exposure.analyzer import ExposureProfile
from app.services.ontology.operations import DetectedOp
from app.services.report.evidence_provider import EvidencedReport
from app.services.risk.score_calculator import OverallScore

logger = structlog.get_logger(__name__)


class ReportGeneratorV3:
    """Assemble the final v3 report from deterministic pipeline outputs.

    This is purely a data assembly step — no risk computation,
    no AI, no external calls. Just formatting.
    """

    def generate(
        self,
        evidenced: EvidencedReport,
        operations: list[DetectedOp],
        exposures: list[ExposureProfile],
        population: str,
        original_filename: str,
        extraction_metadata: dict[str, Any] | None = None,
        summary_text: str | None = None,
        qc_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate the complete v3 report.

        Args:
            evidenced: Scored report with evidence citations
            operations: Detected lab operations
            exposures: Exposure profiles per chemical
            population: Target population
            original_filename: Original protocol filename
            extraction_metadata: Metadata from extraction pipeline
            summary_text: LLM-generated executive summary (optional)
            qc_result: QC check results (optional)

        Returns:
            Complete report dict ready for JSON serialization.
        """
        scores = evidenced.overall_score

        # ── Executive Summary ────────────────────────────────────
        executive_summary = {
            "overall_risk": scores.overall_risk,
            "overall_score": scores.overall_score,
            "total_substances": scores.total_substances,
            "high_risk_count": scores.high_risk_count,
            "critical_count": scores.critical_count,
            "population": population,
            "summary_text": summary_text or "",
        }

        # ── Identified Hazardous Materials ───────────────────────
        substances = []
        for ec in evidenced.chemicals:
            cs = ec.chemical_score
            profile = ec.source_profile or {}
            evidence_list = []
            for ev in ec.evidence:
                evidence_list.append({
                    "source_organization": ev.source_organization,
                    "claim": ev.claim,
                    "claim_domain": ev.claim_domain,
                    "evidence_strength": ev.evidence_strength,
                    "source_document": ev.source_document,
                })

            substances.append({
                "substance_name": cs.canonical_name_en or cs.substance_name,
                "cas_number": cs.cas_number,
                "category": cs.category or "unknown",
                "pregnancy_risk": cs.pregnancy_risk,
                "fertility_risk": cs.fertility_risk,
                "lactation_risk": cs.lactation_risk,
                "pregnancy_score": cs.pregnancy_score,
                "fertility_score": cs.fertility_score,
                "lactation_score": cs.lactation_score,
                "risk_reason": self._build_risk_reason(cs),
                "ghs_classification": profile.get("ghs_classification"),
                "hazard_statements": profile.get("hazard_statements"),
                "effects_on_fetus": profile.get("effects_on_fetus"),
                "effects_on_reproduction": profile.get("effects_on_reproduction"),
                "effects_on_breastfeeding": profile.get("effects_on_breastfeeding"),
                "recommended_ppe": profile.get("recommended_ppe"),
                "recommended_precautions": profile.get("recommended_precautions"),
                "references": profile.get("references"),
                "data_source": profile.get("data_source"),
                "evidence_level": profile.get("evidence_level"),
                "evidence": evidence_list,
                "fired_rules": [
                    {
                        "rule_id": r.rule_id,
                        "rule_name": r.rule_name,
                        "score_contribution": r.score_contribution,
                        "reason": r.rule_reason,
                        "population": r.population,
                    }
                    for r in cs.fired_rules
                ],
            })

        # ── Exposure Analysis ────────────────────────────────────
        exposure_summary = {
            "operations_detected": [
                {
                    "operation_id": op.operation_id,
                    "name_en": op.name_en,
                    "name_zh": op.name_zh,
                    "category": op.category,
                    "primary_exposure_route": op.primary_exposure_route,
                    "risk_modifier": op.risk_modifier,
                    "matched_keyword": op.matched_keyword,
                }
                for op in operations
            ],
            "profiles": [exp.to_dict() for exp in exposures],
        }

        # ── Population-Specific Recommendations ──────────────────
        population_risk = {
            "pregnancy": {
                "max_score": scores.pregnancy_max_score,
                "risk_level": self._score_to_level(scores.pregnancy_max_score),
                "substances_at_risk": [
                    s["substance_name"]
                    for s in substances
                    if s["pregnancy_risk"] in ("High", "Critical")
                ],
            },
            "fertility": {
                "max_score": scores.fertility_max_score,
                "risk_level": self._score_to_level(scores.fertility_max_score),
                "substances_at_risk": [
                    s["substance_name"]
                    for s in substances
                    if s["fertility_risk"] in ("High", "Critical")
                ],
            },
            "lactation": {
                "max_score": scores.lactation_max_score,
                "risk_level": self._score_to_level(scores.lactation_max_score),
                "substances_at_risk": [
                    s["substance_name"]
                    for s in substances
                    if s["lactation_risk"] in ("High", "Critical")
                ],
            },
        }

        # ── Safety Controls ──────────────────────────────────────
        safety_controls = self._build_safety_controls(substances, operations)

        # ── Evidence Summary ─────────────────────────────────────
        evidence_summary = {
            "total_citations": evidenced.total_citations,
            "sources_used": evidenced.sources_used,
            "general_evidence": [
                {
                    "source_organization": e.source_organization,
                    "claim": e.claim,
                    "source_document": e.source_document,
                }
                for e in evidenced.general_evidence
            ],
        }

        # ── Metadata ─────────────────────────────────────────────
        metadata = {
            "version": "3.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline": {
                "extraction": extraction_metadata or {},
                "operations_detected": len(operations),
                "rules_fired": len(scores.all_fired_rules),
                "evidence_citations": evidenced.total_citations,
            },
            "qc": qc_result or {},
        }

        # ── Assemble Report ──────────────────────────────────────
        report = {
            "original_filename": original_filename,
            "overall_risk": scores.overall_risk,
            "overall_score": scores.overall_score,
            "executive_summary": executive_summary,
            "identified_hazardous_materials": substances,
            "population_risk": population_risk,
            "exposure_analysis": exposure_summary,
            "safety_controls": safety_controls,
            "evidence_summary": evidence_summary,
            "metadata": metadata,
            "disclaimer": (
                "This report is a laboratory safety reference tool based on deterministic "
                "risk assessment rules and published toxicological evidence. It does not "
                "replace professional occupational health consultation or institutional "
                "EHS review. All risk scores are computed from rule-based analysis, not AI "
                "generation. Evidence sources include NIOSH, OSHA, IARC, PubChem, ECHA, "
                "and LactMed. Always consult your physician or institutional safety officer "
                "before making decisions based on this assessment."
            ),
        }

        logger.info(
            "report_generated_v3",
            substances=len(substances),
            operations=len(operations),
            risk_level=scores.overall_risk,
            score=scores.overall_score,
            evidence_citations=evidenced.total_citations,
        )
        return report

    # ── Private helpers ──────────────────────────────────────────

    @staticmethod
    def _score_to_level(score: int) -> str:
        if score >= 75:
            return "Critical"
        elif score >= 50:
            return "High"
        elif score >= 25:
            return "Moderate"
        return "Low"

    @staticmethod
    def _build_risk_reason(cs: Any) -> str:
        """Build a human-readable risk reason from fired rules."""
        if not cs.fired_rules:
            return "No specific risk rules triggered."

        reasons = []
        for r in cs.fired_rules[:5]:  # Top 5
            reasons.append(r.rule_reason)

        if cs.cas_number:
            return f"[CAS: {cs.cas_number}] " + "; ".join(reasons)
        return "; ".join(reasons)

    @staticmethod
    def _build_safety_controls(
        substances: list[dict[str, Any]],
        operations: list[DetectedOp],
    ) -> dict[str, Any]:
        """Build safety control recommendations."""
        # Engineering controls from operations
        engineering = []
        ppe = set()
        operational = []

        for op in operations:
            if op.requires_containment:
                engineering.append(
                    f"{op.name_en}: requires containment ({op.primary_exposure_route} exposure)"
                )
            if op.aerosol_generation:
                engineering.append(
                    f"{op.name_en}: aerosol generation — use fume hood or biosafety cabinet"
                )
                ppe.add("Respirator (N95 or better)")

        # PPE from substances
        for s in substances:
            risk = s.get("pregnancy_risk", "Low")
            if risk in ("High", "Critical"):
                ppe.add("Double nitrile or butyl rubber gloves")
                ppe.add("Safety goggles or face shield")
                ppe.add("Lab coat (flame-resistant if needed)")

        # Always-recommended basics
        ppe.add("Lab coat")
        ppe.add("Safety glasses")
        ppe.add("Nitrile gloves")
        ppe.add("Closed-toe shoes")

        # Operational controls
        high_risk = [s for s in substances if s.get("pregnancy_risk") in ("High", "Critical")]
        if high_risk:
            operational.append(
                f"Minimize handling time for {len(high_risk)} high-risk substances"
            )
        operational.append("No eating, drinking, or applying cosmetics in lab")
        operational.append("Wash hands thoroughly after handling chemicals")
        operational.append("Decontaminate work surfaces after use")

        return {
            "engineering_controls": list(set(engineering)),
            "recommended_ppe": sorted(ppe),
            "operational_procedures": operational,
        }
