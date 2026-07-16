"""Structured risk assessment report generator.

Produces the final JSON report from assessed substances including
risk scoring, population-specific breakdowns, and safety recommendations.
"""

from __future__ import annotations

import structlog
from collections import Counter

from app.core.enums import RiskLevel

logger = structlog.get_logger(__name__)

# ── Risk scoring constants ────────────────────────────────────
# Normalized per-population weights for overall score calculation
RISK_WEIGHTS: dict[str, int] = {
    RiskLevel.HIGH_RISK: 10,
    RiskLevel.MODERATE_RISK: 5,
    RiskLevel.UNKNOWN: 3,
    RiskLevel.LOW_RISK: 2,
    RiskLevel.SAFE: 0,
}

POPULATION_FIELDS = ("pregnancy_risk", "fertility_risk", "lactation_risk")

DISCLAIMER_TEXT = (
    "本报告仅供实验室安全参考，不能替代职业健康专家建议。"
    "使用前请咨询您的医生或职业健康顾问。"
)


class ReportGenerator:
    """Generate structured risk assessment reports from assessed substances."""

    def generate(self, substances: list[dict], filename: str) -> dict:
        """Generate a full structured report.

        Args:
            substances: List of assessed substance dicts (from RiskMatcher).
            filename: Original protocol filename for the report header.

        Returns:
            A complete report dictionary matching the ReportDetail schema.
        """
        if not substances:
            logger.info("report_generated_empty", filename=filename)
            return self._empty_report(filename)

        # ── Count risk levels across populations ──────────────
        all_risks: list[str] = []
        pregnancy_risks: list[str] = []
        fertility_risks: list[str] = []
        lactation_risks: list[str] = []

        for s in substances:
            for field, collector in [
                ("pregnancy_risk", pregnancy_risks),
                ("fertility_risk", fertility_risks),
                ("lactation_risk", lactation_risks),
            ]:
                risk = s.get(field, RiskLevel.UNKNOWN)
                collector.append(risk)
                all_risks.append(risk)

        # ── Overall score ─────────────────────────────────────
        overall_score = self._calculate_overall_score(substances)
        overall_risk = self._score_to_risk_label(overall_score)

        # ── Executive summary ─────────────────────────────────
        high_count = all_risks.count(RiskLevel.HIGH_RISK)
        moderate_count = all_risks.count(RiskLevel.MODERATE_RISK)
        low_count = all_risks.count(RiskLevel.LOW_RISK)
        safe_count = all_risks.count(RiskLevel.SAFE)

        executive_summary = {
            "total_substances_found": len(substances),
            "high_risk_count": high_count,
            "moderate_risk_count": moderate_count,
            "low_risk_count": low_count,
            "safe_count": safe_count,
            "summary_text": self._generate_summary_text(
                len(substances), high_count, moderate_count, low_count, overall_risk
            ),
        }

        # ── Identified materials ──────────────────────────────
        materials = self._build_materials_list(substances)

        # ── High risk items (sorted by severity) ──────────────
        high_risk = sorted(
            [m for m in materials if self._is_high_risk(m)],
            key=lambda x: self._max_risk_score(x),
            reverse=True,
        )

        # ── Recommended precautions ───────────────────────────
        precautions = self._build_precautions(substances)

        # ── Risk by population ────────────────────────────────
        risk_by_category = {
            "妊娠期": self._count_risks(pregnancy_risks),
            "备孕期": self._count_risks(fertility_risks),
            "哺乳期": self._count_risks(lactation_risks),
        }

        logger.info(
            "report_generated",
            filename=filename,
            score=overall_score,
            risk=overall_risk,
            substances=len(substances),
            high=high_count,
        )

        return {
            "original_filename": filename,
            "overall_risk": overall_risk,
            "overall_score": overall_score,
            "executive_summary": executive_summary,
            "identified_hazardous_materials": materials,
            "high_risk_items": high_risk,
            "recommended_precautions": precautions,
            "risk_by_category": risk_by_category,
            "disclaimer": DISCLAIMER_TEXT,
        }

    # ── Scoring ───────────────────────────────────────────────

    def _calculate_overall_score(self, substances: list[dict]) -> int:
        """Calculate a 0-100 overall risk score using weighted aggregation.

        Considers all three populations per substance, normalizing against
        the theoretical maximum (all High Risk).
        """
        if not substances:
            return 0

        total_weight = 0
        for s in substances:
            for pop in POPULATION_FIELDS:
                risk = s.get(pop, RiskLevel.UNKNOWN)
                total_weight += RISK_WEIGHTS.get(risk, 3)

        # Max possible: all substances × 3 populations × 10 (High Risk)
        max_possible = len(substances) * len(POPULATION_FIELDS) * max(RISK_WEIGHTS.values())
        if max_possible == 0:
            return 0

        score = min(100, int((total_weight / max_possible) * 100))
        return score

    @staticmethod
    def _score_to_risk_label(score: int) -> str:
        """Map numeric score to a risk label."""
        if score >= 70:
            return "High"
        elif score >= 30:
            return "Medium"
        return "Low"

    @staticmethod
    def _is_high_risk(item: dict) -> bool:
        """Check if any population risk is High for this item."""
        for pop in POPULATION_FIELDS:
            if RiskLevel.HIGH_RISK == item.get(pop, ""):
                return True
        return False

    @staticmethod
    def _max_risk_score(item: dict) -> int:
        """Get the highest risk score across all populations for an item."""
        scores = [RISK_WEIGHTS.get(item.get(p, RiskLevel.UNKNOWN), 0) for p in POPULATION_FIELDS]
        return max(scores)

    # ── Building helpers ──────────────────────────────────────

    @staticmethod
    def _build_materials_list(substances: list[dict]) -> list[dict]:
        """Build the identified hazardous materials list."""
        materials = []
        for s in substances:
            materials.append({
                "id": s.get("id", 0),
                "substance_name": s["substance_name"],
                "category": s.get("category", ""),
                "pregnancy_risk": s.get("pregnancy_risk", RiskLevel.UNKNOWN),
                "fertility_risk": s.get("fertility_risk", RiskLevel.UNKNOWN),
                "lactation_risk": s.get("lactation_risk", RiskLevel.UNKNOWN),
                "risk_reason": s.get("risk_reason", ""),
                "effects_on_fetus": s.get("effects_on_fetus", ""),
                "effects_on_reproduction": s.get("effects_on_reproduction", ""),
                "effects_on_breastfeeding": s.get("effects_on_breastfeeding", ""),
                "exposure_routes": s.get("exposure_routes", []),
                "recommended_ppe": s.get("recommended_ppe", ""),
                "recommended_precautions": s.get("recommended_precautions", ""),
                "found_in_section": s.get("found_in_section", ""),
            })
        return materials

    @staticmethod
    def _build_precautions(substances: list[dict]) -> list[dict]:
        """Build precautions list for moderate and high risk substances."""
        precautions = []
        for s in substances:
            risk = s.get("pregnancy_risk", RiskLevel.UNKNOWN)
            if risk in (RiskLevel.HIGH_RISK, RiskLevel.MODERATE_RISK):
                prec_text = s.get("recommended_precautions", "")
                prec_lines = [
                    p.strip().lstrip("✓").strip()
                    for p in prec_text.split("\n")
                    if p.strip()
                ]
                precautions.append({
                    "substance_name": s["substance_name"],
                    "risk": risk,
                    "precautions": prec_lines or ["使用标准实验室PPE"],
                })
        return precautions

    @staticmethod
    def _count_risks(risks: list[str]) -> dict:
        """Count risk levels for a population group."""
        return {
            "high": risks.count(RiskLevel.HIGH_RISK),
            "moderate": risks.count(RiskLevel.MODERATE_RISK),
            "low": risks.count(RiskLevel.LOW_RISK),
            "safe": risks.count(RiskLevel.SAFE),
        }

    @staticmethod
    def _generate_summary_text(
        total: int, high: int, moderate: int, low: int, overall: str
    ) -> str:
        """Generate a Chinese-language executive summary text."""
        if total == 0:
            return "该protocol中未识别出已知危险物质。但仍建议在操作前进行额外的安全评估。"

        parts = [f"该实验protocol中共识别出 {total} 种潜在危险物质。"]
        if high > 0:
            parts.append(f"其中 {high} 项被评估为高风险，强烈建议采取严格防护措施或考虑替代方案。")
        if moderate > 0:
            parts.append(f"{moderate} 项为中等风险，需要加强防护。")
        if low > 0:
            parts.append(f"{low} 项为低风险，标准实验室操作即可。")
        parts.append(f"总体风险评估为：{overall}。")
        return "".join(parts)

    @staticmethod
    def _empty_report(filename: str) -> dict:
        """Return an empty report structure when no substances found."""
        empty_risks = {"high": 0, "moderate": 0, "low": 0, "safe": 0}
        return {
            "original_filename": filename,
            "overall_risk": "Low",
            "overall_score": 0,
            "executive_summary": {
                "total_substances_found": 0,
                "high_risk_count": 0,
                "moderate_risk_count": 0,
                "low_risk_count": 0,
                "safe_count": 0,
                "summary_text": "该protocol中未识别出已知危险物质。但仍建议在操作前进行额外的安全评估。",
            },
            "identified_hazardous_materials": [],
            "high_risk_items": [],
            "recommended_precautions": [],
            "risk_by_category": {
                "妊娠期": empty_risks,
                "备孕期": empty_risks,
                "哺乳期": empty_risks,
            },
            "disclaimer": DISCLAIMER_TEXT,
        }
