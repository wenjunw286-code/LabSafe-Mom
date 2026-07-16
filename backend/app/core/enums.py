"""Domain enumerations for LabSafe Mom.

Eliminates magic string comparisons across the codebase.
"""

from enum import StrEnum


class RiskLevel(StrEnum):
    """Reproductive risk level for a substance against a specific population."""

    SAFE = "Safe"
    LOW_RISK = "Low Risk"
    MODERATE_RISK = "Moderate Risk"
    HIGH_RISK = "High Risk"
    UNKNOWN = "Unknown"

    @classmethod
    def from_string(cls, value: str) -> "RiskLevel":
        """Safely parse a string into a RiskLevel, defaulting to UNKNOWN."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN

    @property
    def numeric_value(self) -> int:
        """Numeric score for risk aggregation (higher = more risky)."""
        mapping = {
            RiskLevel.SAFE: 0,
            RiskLevel.LOW_RISK: 2,
            RiskLevel.UNKNOWN: 3,
            RiskLevel.MODERATE_RISK: 5,
            RiskLevel.HIGH_RISK: 10,
        }
        return mapping[self]

    @property
    def display_emoji(self) -> str:
        """Display emoji for UI rendering."""
        mapping = {
            RiskLevel.SAFE: "\U0001f7e2",           # 🟢
            RiskLevel.LOW_RISK: "\U0001f7e1",       # 🟡
            RiskLevel.MODERATE_RISK: "\U0001f7e0",  # 🟠
            RiskLevel.HIGH_RISK: "\U0001f534",      # 🔴
            RiskLevel.UNKNOWN: "⚪",            # ⚪
        }
        return mapping[self]


class SubstanceCategory(StrEnum):
    """Categories of hazardous laboratory substances."""

    CHEMICAL_REAGENT = "化学试剂"
    BIOLOGICAL_AGENT = "生物试剂"
    DYE = "染料"
    FIXATIVE = "固定液"
    ORGANIC_SOLVENT = "有机溶剂"
    ANTIBIOTIC = "抗生素"
    RADIOACTIVE = "放射性物质"
    ANESTHETIC = "麻醉剂"
    OTHER = "其他"

    @classmethod
    def from_string(cls, value: str) -> "SubstanceCategory":
        """Safely parse a string into a SubstanceCategory, defaulting to OTHER."""
        try:
            return cls(value)
        except ValueError:
            return cls.OTHER


class ReportStatus(StrEnum):
    """Lifecycle status of an analysis report."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PopulationType(StrEnum):
    """Target population groups for risk assessment."""

    PREGNANCY = "妊娠期"
    FERTILITY = "备孕期"
    LACTATION = "哺乳期"


class FeedbackType(StrEnum):
    """Types of user feedback on risk assessments."""

    AGREE = "agree"
    DISAGREE = "disagree"
    CORRECTION = "correction"
    COMMENT = "comment"
