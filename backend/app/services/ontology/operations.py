"""Lab Operation Detector — scans protocol text for known lab operations.

Uses the YAML ontology (ontology.yaml) to detect operations by keyword
matching. Each detected operation infers exposure routes and risk modifiers
for downstream analysis.
"""

from __future__ import annotations

import re
from pathlib import Path

import structlog
import yaml
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# ── Schemas ──────────────────────────────────────────────────────

class OperationDef(BaseModel):
    """A single operation definition from ontology.yaml."""

    id: str
    name_en: str
    name_zh: str
    category: str
    primary_exposure_route: str
    secondary_exposure_routes: list[str] = Field(default_factory=list)
    aerosol_generation: bool = False
    volatile_release: bool = False
    powder_handling: bool = False
    requires_containment: bool = False
    risk_modifier: int = 0
    trigger_keywords_en: list[str] = Field(default_factory=list)
    trigger_keywords_zh: list[str] = Field(default_factory=list)


class DetectedOp(BaseModel):
    """An operation detected in a protocol."""

    operation_id: str
    name_en: str
    name_zh: str
    category: str
    primary_exposure_route: str
    secondary_exposure_routes: list[str]
    aerosol_generation: bool
    volatile_release: bool
    powder_handling: bool
    requires_containment: bool
    risk_modifier: int
    found_in_section: str
    matched_keyword: str


# ── Detector ─────────────────────────────────────────────────────

class LabOperationDetector:
    """Detect lab operations in protocol text via keyword matching.

    Loads the YAML ontology at init time. Detection is deterministic —
    scans text for trigger keywords and returns all matching operations.

    Usage:
        detector = LabOperationDetector()
        ops = detector.detect(protocol_text)
        for op in ops:
            print(f"{op.name_en}: {op.matched_keyword}")
    """

    def __init__(self, ontology_path: str | None = None):
        if ontology_path is None:
            ontology_path = str(
                Path(__file__).parent.parent.parent / "data" / "ontology.yaml"
            )
        self._path = Path(ontology_path)
        self._operations: list[OperationDef] = []
        self._load()

    def _load(self) -> None:
        """Load and validate ontology from YAML."""
        if not self._path.exists():
            logger.warning("ontology_file_not_found", path=str(self._path))
            return

        raw = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        for raw_op in raw.get("operations", []):
            self._operations.append(OperationDef.model_validate(raw_op))

        logger.info("ontology_loaded", count=len(self._operations))

    @property
    def operation_count(self) -> int:
        return len(self._operations)

    def detect(self, text: str) -> list[DetectedOp]:
        """Detect all lab operations mentioned in the protocol text.

        Args:
            text: Full protocol text to scan.

        Returns:
            List of detected operations with matched keywords and context.
        """
        if not text:
            return []

        text_lower = text.lower()
        detected: list[DetectedOp] = []
        seen_ids: set[str] = set()

        for op_def in self._operations:
            if op_def.id in seen_ids:
                continue

            # Check English keywords
            for kw in op_def.trigger_keywords_en:
                if kw.lower() in text_lower:
                    detected.append(self._build_result(op_def, text, kw))
                    seen_ids.add(op_def.id)
                    break

            if op_def.id in seen_ids:
                continue

            # Check Chinese keywords
            for kw in op_def.trigger_keywords_zh:
                if kw in text:
                    detected.append(self._build_result(op_def, text, kw))
                    seen_ids.add(op_def.id)
                    break

        logger.info(
            "operations_detected",
            total=len(detected),
            operations=[d.name_en for d in detected],
        )
        return detected

    def _build_result(
        self,
        op_def: OperationDef,
        text: str,
        matched_keyword: str,
    ) -> DetectedOp:
        """Build a DetectedOp with surrounding context."""
        # Extract surrounding context (200 chars around the match)
        idx = text.lower().find(matched_keyword.lower())
        if idx >= 0:
            start = max(0, idx - 100)
            end = min(len(text), idx + len(matched_keyword) + 100)
            context = text[start:end].strip()
        else:
            context = ""

        return DetectedOp(
            operation_id=op_def.id,
            name_en=op_def.name_en,
            name_zh=op_def.name_zh,
            category=op_def.category,
            primary_exposure_route=op_def.primary_exposure_route,
            secondary_exposure_routes=op_def.secondary_exposure_routes,
            aerosol_generation=op_def.aerosol_generation,
            volatile_release=op_def.volatile_release,
            powder_handling=op_def.powder_handling,
            requires_containment=op_def.requires_containment,
            risk_modifier=op_def.risk_modifier,
            found_in_section=context,
            matched_keyword=matched_keyword,
        )

    def get_all_operations(self) -> list[OperationDef]:
        """Return all defined operations (for UI/search)."""
        return list(self._operations)


# Module-level singleton
_detector: LabOperationDetector | None = None


def get_operation_detector() -> LabOperationDetector:
    global _detector
    if _detector is None:
        _detector = LabOperationDetector()
    return _detector
