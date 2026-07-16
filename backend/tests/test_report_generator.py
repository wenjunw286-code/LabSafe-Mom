"""Unit tests for ReportGenerator service."""

from __future__ import annotations

from app.services.report_generator import ReportGenerator


class TestReportGenerator:
    """Test suite for report generation."""

    def test_empty_report(self):
        """Should generate an empty report when no substances found."""
        generator = ReportGenerator()
        result = generator.generate([], "test_protocol.pdf")

        assert result["overall_risk"] == "Low"
        assert result["overall_score"] == 0
        assert result["executive_summary"]["total_substances_found"] == 0
        assert result["identified_hazardous_materials"] == []
        assert result["high_risk_items"] == []

    def test_single_high_risk_substance(self):
        """Should correctly score a single high-risk substance."""
        generator = ReportGenerator()
        substances = [
            {
                "substance_name": "Formaldehyde",
                "category": "固定液",
                "pregnancy_risk": "High Risk",
                "fertility_risk": "High Risk",
                "lactation_risk": "Moderate Risk",
                "risk_reason": "Known teratogen",
                "effects_on_fetus": "Developmental abnormalities",
                "effects_on_reproduction": "Reduced fertility",
                "effects_on_breastfeeding": "May transfer to milk",
                "exposure_routes": ["吸入", "皮肤接触"],
                "recommended_ppe": "Chemical hood, double gloves",
                "recommended_precautions": "✓ Use in hood\n✓ Wear gloves",
                "found_in_section": "Fixation step",
            }
        ]
        result = generator.generate(substances, "test.pdf")

        assert result["overall_score"] > 50  # High risk should score high
        assert result["overall_risk"] in ("High", "Medium")
        assert len(result["identified_hazardous_materials"]) == 1
        assert len(result["high_risk_items"]) == 1

    def test_safe_substance_scores_low(self):
        """Should score safe substances at 0."""
        generator = ReportGenerator()
        substances = [
            {
                "substance_name": "Glycerol",
                "category": "化学试剂",
                "pregnancy_risk": "Safe",
                "fertility_risk": "Safe",
                "lactation_risk": "Safe",
                "risk_reason": "",
                "effects_on_fetus": "",
                "effects_on_reproduction": "",
                "effects_on_breastfeeding": "",
                "exposure_routes": [],
                "recommended_ppe": "",
                "recommended_precautions": "",
                "found_in_section": "",
            }
        ]
        result = generator.generate(substances, "test.pdf")

        assert result["overall_score"] == 0
        assert result["overall_risk"] == "Low"

    def test_mixed_risk_substances(self):
        """Should aggregate multiple risk levels correctly."""
        generator = ReportGenerator()
        substances = [
            {
                "substance_name": "HighRisk",
                "category": "固定液",
                "pregnancy_risk": "High Risk",
                "fertility_risk": "High Risk",
                "lactation_risk": "High Risk",
                "risk_reason": "",
                "effects_on_fetus": "",
                "effects_on_reproduction": "",
                "effects_on_breastfeeding": "",
                "exposure_routes": [],
                "recommended_ppe": "",
                "recommended_precautions": "",
                "found_in_section": "",
            },
            {
                "substance_name": "SafeThing",
                "category": "化学试剂",
                "pregnancy_risk": "Safe",
                "fertility_risk": "Safe",
                "lactation_risk": "Safe",
                "risk_reason": "",
                "effects_on_fetus": "",
                "effects_on_reproduction": "",
                "effects_on_breastfeeding": "",
                "exposure_routes": [],
                "recommended_ppe": "",
                "recommended_precautions": "",
                "found_in_section": "",
            },
        ]
        result = generator.generate(substances, "test.pdf")

        # Should have 1 high-risk item
        assert len(result["high_risk_items"]) == 1
        # Overall score should be mid-range (one high, one safe)
        assert 0 < result["overall_score"] < 100
