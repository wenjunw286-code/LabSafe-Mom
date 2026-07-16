"""Exposure Analyzer — infers exposure conditions from protocol text.

Analyzes protocol text and detected lab operations to infer:
- Ventilation conditions (fume hood, open bench, biosafety cabinet)
- Temperature (ambient, cold, elevated, cryogenic)
- Frequency (once, daily, weekly, continuous)
- Volume and concentration ranges
- Exposure routes per chemical

All inference is deterministic keyword/regex-based — no LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.services.ontology.operations import DetectedOp

logger = structlog.get_logger(__name__)


@dataclass
class ExposureProfile:
    """Inferred exposure conditions for a specific chemical/protocol."""

    ventilation: str = "unknown"  # fume_hood, open_bench, biosafety_cabinet, glove_box
    temperature: str = "ambient"  # ambient, cold, elevated, cryogenic
    frequency: str = "once"  # once, daily, weekly, continuous
    duration_min: int | None = None
    volume_ml: float | None = None
    concentration_pct: float | None = None
    is_powder: bool = False
    is_liquid: bool = True
    exposure_routes: list[str] = field(default_factory=list)
    risk_modifier: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ventilation": self.ventilation,
            "temperature": self.temperature,
            "frequency": self.frequency,
            "duration_min": self.duration_min,
            "volume_ml": self.volume_ml,
            "concentration_pct": self.concentration_pct,
            "is_powder": self.is_powder,
            "is_liquid": self.is_liquid,
            "exposure_routes": self.exposure_routes,
            "risk_modifier": self.risk_modifier,
        }


class ExposureAnalyzer:
    """Infer exposure conditions from protocol text and operations.

    Uses keyword and regex matching — fully deterministic, no LLM.
    """

    # ── Ventilation keywords ─────────────────────────────────────
    FUME_HOOD_PATTERNS = [
        r"fume\s*hood", r"chemical\s*hood", r"通风橱", r"通风柜",
        r"排风柜", r"fume\s*cupboard",
    ]
    BIOSAFETY_PATTERNS = [
        r"biosafety\s*cabinet", r"biological\s*safety\s*cabinet",
        r"BSC", r"生物安全柜", r"超净台", r"超净工作台",
        r"laminar\s*flow\s*hood", r"clean\s*bench",
    ]
    GLOVE_BOX_PATTERNS = [
        r"glove\s*box", r"glovebox", r"手套箱", r"厌氧箱",
        r"sealed\s*container", r"密闭容器",
    ]

    FUME_HOOD_NEGATION_PATTERNS = [
        r"outside\s+(?:the\s+)?fume\s*hood",
        r"not\s+(?:in|inside|under)\s+(?:the\s+)?fume\s*hood",
        r"without\s+(?:a\s+)?fume\s*hood",
        r"fume\s*hood\s+(?:off|not\s+running|not\s+on)",
        r"\u901a\u98ce\u6a71\u5916",
        r"\u901a\u98ce\u6a71.{0,8}\u672a\u5f00",
        r"\u901a\u98ce\u6a71.{0,8}\u6ca1\u5f00",
        r"\u901a\u98ce\u6a71.{0,8}\u672a\u542f\u52a8",
        r"\u901a\u98ce\u6a71.{0,8}\u672a\u5f00\u542f",
        r"\u672a\u5728\u901a\u98ce\u6a71",
        r"\u4e0d\u5728\u901a\u98ce\u6a71",
        r"\u65e0\u901a\u98ce\u6a71",
        r"\u6ca1\u6709\u901a\u98ce\u6a71",
    ]

    # ── Temperature patterns ─────────────────────────────────────
    COLD_PATTERNS = [
        r"4°C", r"on\s*ice", r"ice\s*cold", r"冰上", r"冰浴",
        r"refrigerat", r"冷藏", r"cold\s*room", r"冷库",
        r"2-?8°C", r"2-?8\s*°C",
    ]
    ELEVATED_PATTERNS = [
        r"37°C", r"heat", r"加热", r"boil", r"煮沸", r"水浴",
        r"water\s*bath", r"incubat", r"培养", r"reflux", r"回流",
        r"95°C", r"100°C", r"65°C", r"56°C", r"42°C",
        r"hot\s*plate", r"加热板", r"microwave", r"微波",
    ]
    CRYOGENIC_PATTERNS = [
        r"liquid\s*nitrogen", r"液氮", r"LN2", r"-80°C", r"-80\s*°C",
        r"-196°C", r"cryo", r"低温", r"deep\s*freezer",
    ]

    # ── Frequency patterns ───────────────────────────────────────
    DAILY_PATTERNS = [r"daily", r"每天", r"每日", r"every\s*day"]
    WEEKLY_PATTERNS = [r"weekly", r"每周", r"every\s*week", r"once\s*a\s*week"]
    CONTINUOUS_PATTERNS = [
        r"continuous", r"连续", r"overnight", r"过夜", r"constant",
        r"ongoing", r"持续",
    ]

    # ── Volume extraction ────────────────────────────────────────
    VOLUME_PATTERN = re.compile(
        r"(\d+(?:\.\d+)?)\s*(ml|mL|μl|ul|L|litre|liter|liters?)",
        re.IGNORECASE,
    )

    # ── Concentration extraction ─────────────────────────────────
    CONC_PCT_PATTERN = re.compile(
        r"(\d+(?:\.\d+)?)\s*%", re.IGNORECASE
    )
    CONC_MOLAR_PATTERN = re.compile(
        r"(\d+(?:\.\d+)?)\s*(M|mM|μM|uM|nM)\b"
    )

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile all regex patterns."""
        self._fume_hood = [re.compile(p, re.IGNORECASE) for p in self.FUME_HOOD_PATTERNS]
        self._fume_hood_negation = [re.compile(p, re.IGNORECASE) for p in self.FUME_HOOD_NEGATION_PATTERNS]
        self._biosafety = [re.compile(p, re.IGNORECASE) for p in self.BIOSAFETY_PATTERNS]
        self._glove_box = [re.compile(p, re.IGNORECASE) for p in self.GLOVE_BOX_PATTERNS]
        self._cold = [re.compile(p, re.IGNORECASE) for p in self.COLD_PATTERNS]
        self._elevated = [re.compile(p, re.IGNORECASE) for p in self.ELEVATED_PATTERNS]
        self._cryogenic = [re.compile(p, re.IGNORECASE) for p in self.CRYOGENIC_PATTERNS]
        self._daily = [re.compile(p, re.IGNORECASE) for p in self.DAILY_PATTERNS]
        self._weekly = [re.compile(p, re.IGNORECASE) for p in self.WEEKLY_PATTERNS]
        self._continuous = [re.compile(p, re.IGNORECASE) for p in self.CONTINUOUS_PATTERNS]

    def _match_any(self, patterns: list[re.Pattern], text: str) -> bool:
        """Check if any pattern matches the text."""
        return any(p.search(text) for p in patterns)

    def analyze(
        self,
        text: str,
        operations: list[DetectedOp],
        chemicals: list[dict[str, Any]],
    ) -> list[ExposureProfile]:
        """Analyze exposure conditions for each chemical.

        Args:
            text: Full protocol text
            operations: Detected lab operations from LabOperationDetector
            chemicals: Chemical identity dicts

        Returns:
            One ExposureProfile per chemical.
        """
        # Global exposure conditions from text
        ventilation = self._infer_ventilation(text)
        temperature = self._infer_temperature(text)
        frequency = self._infer_frequency(text)
        volume = self._extract_volume(text)
        concentration = self._extract_concentration(text)

        # Collect all exposure routes from operations
        all_routes: set[str] = set()
        total_risk_modifier = 0
        is_powder = False

        for op in operations:
            all_routes.add(op.primary_exposure_route)
            all_routes.update(op.secondary_exposure_routes)
            total_risk_modifier += op.risk_modifier
            if op.powder_handling:
                is_powder = True
            # Operations with containment imply better ventilation
            if op.requires_containment and ventilation == "open_bench":
                # Don't override user-specified conditions
                pass

        # Create profiles — one per chemical, with per-chemical overrides
        profiles: list[ExposureProfile] = []
        for chem in chemicals:
            chem_name = chem.get("canonical_name_en", "")
            chem_volatile = chem.get("volatile", False)
            chem_dermal = chem.get("dermal_absorption", False)

            routes = list(all_routes)
            # Add chemical-specific exposure routes based on properties
            if chem_volatile:
                if "inhalation" not in routes:
                    routes.append("inhalation")
            if chem_dermal:
                if "dermal" not in routes:
                    routes.append("dermal")

            profile = ExposureProfile(
                ventilation=ventilation,
                temperature=temperature,
                frequency=frequency,
                duration_min=None,
                volume_ml=volume,
                concentration_pct=concentration,
                is_powder=is_powder,
                is_liquid=not is_powder,
                exposure_routes=routes,
                risk_modifier=total_risk_modifier,
            )
            profiles.append(profile)

        logger.info(
            "exposure_analysis_complete",
            ventilation=ventilation,
            temperature=temperature,
            frequency=frequency,
            operations_count=len(operations),
            chemicals_count=len(chemicals),
        )
        return profiles

    def analyze_single(
        self,
        text: str,
        operations: list[DetectedOp],
    ) -> ExposureProfile:
        """Analyze exposure for a single chemical (convenience method)."""
        profiles = self.analyze(text, operations, [{}])
        return profiles[0] if profiles else ExposureProfile()

    # ── Private inference methods ────────────────────────────────

    def _infer_ventilation(self, text: str) -> str:
        """Infer ventilation type from text."""
        if self._match_any(self._fume_hood_negation, text):
            return "open_bench"
        if self._match_any(self._fume_hood, text):
            return "fume_hood"
        if self._match_any(self._glove_box, text):
            return "glove_box"
        if self._match_any(self._biosafety, text):
            return "biosafety_cabinet"
        return "open_bench"

    def _infer_temperature(self, text: str) -> str:
        """Infer temperature conditions from text."""
        if self._match_any(self._cryogenic, text):
            return "cryogenic"
        if self._match_any(self._elevated, text):
            return "elevated"
        if self._match_any(self._cold, text):
            return "cold"
        return "ambient"

    def _infer_frequency(self, text: str) -> str:
        """Infer exposure frequency from text."""
        if self._match_any(self._continuous, text):
            return "continuous"
        if self._match_any(self._daily, text):
            return "daily"
        if self._match_any(self._weekly, text):
            return "weekly"
        return "once"

    def _extract_volume(self, text: str) -> float | None:
        """Extract maximum volume mentioned in text (ml)."""
        volumes = []
        for match in self.VOLUME_PATTERN.finditer(text):
            val = float(match.group(1))
            unit = match.group(2).lower()
            # Normalize to ml
            if unit in ("μl", "ul"):
                val /= 1000
            elif unit in ("l", "litre", "liter", "liters"):
                val *= 1000
            volumes.append(val)
        return max(volumes) if volumes else None

    def _extract_concentration(self, text: str) -> float | None:
        """Extract maximum concentration from text (as percentage)."""
        concentrations = []
        for match in self.CONC_PCT_PATTERN.finditer(text):
            concentrations.append(float(match.group(1)))
        # Approximate molar → percentage (rough: 1M ≈ 10% for small molecules)
        for match in self.CONC_MOLAR_PATTERN.finditer(text):
            val = float(match.group(1))
            unit = match.group(2)
            if unit == "M":
                concentrations.append(min(val * 10, 100))
            elif unit == "mM":
                concentrations.append(val / 100)
        return max(concentrations) if concentrations else None


# Module-level singleton
_analyzer: ExposureAnalyzer | None = None


def get_exposure_analyzer() -> ExposureAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = ExposureAnalyzer()
    return _analyzer
