"""Lab Operation Ontology ORM models — SQLAlchemy 2.0 style.

Defines the laboratory operation ontology (LabOperation), per-report
detected operations (DetectedOperation), and rule engine audit trail
(RuleEvaluation).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class LabOperation(Base):
    """Laboratory operation ontology entry.

    Each row defines one type of lab operation with its associated
    exposure routes, risk modifiers, and trigger keywords for detection.
    """

    __tablename__ = "lab_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    name_zh: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "chemical_handling", "physical", "biological", "analytical"
    primary_exposure_route: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "inhalation", "dermal", "ocular", "oral", "injection"
    secondary_exposure_routes: Mapped[list[str]] = mapped_column(
        JSON, default=list
    )
    aerosol_generation: Mapped[bool] = mapped_column(Boolean, default=False)
    volatile_release: Mapped[bool] = mapped_column(Boolean, default=False)
    powder_handling: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_containment: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_modifier: Mapped[int] = mapped_column(
        Integer, default=0
    )  # +0 to +30 added to risk score
    trigger_keywords_en: Mapped[list[str]] = mapped_column(JSON, default=list)
    trigger_keywords_zh: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DetectedOperation(Base):
    """Operations detected in a specific analysis report.

    Each row records one lab operation found in the protocol text,
    along with inferred exposure-relevant parameters.
    """

    __tablename__ = "detected_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("analysis_reports.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    operation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lab_operations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    found_in_section: Mapped[str | None] = mapped_column(Text, default=None)
    inferred_temperature: Mapped[str | None] = mapped_column(
        String(20), default=None
    )  # "ambient", "cold", "elevated", "cryogenic"
    inferred_ventilation: Mapped[str | None] = mapped_column(
        String(30), default=None
    )  # "fume_hood", "open_bench", "biosafety_cabinet", "glove_box"
    inferred_volume_ml: Mapped[float | None] = mapped_column(Float, default=None)
    inferred_concentration_pct: Mapped[float | None] = mapped_column(
        Float, default=None
    )
    inferred_frequency: Mapped[str | None] = mapped_column(
        String(20), default=None
    )  # "once", "daily", "weekly", "continuous"
    inferred_duration_min: Mapped[int | None] = mapped_column(Integer, default=None)
    raw_context: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RuleEvaluation(Base):
    """Audit trail: which rules fired for which substances.

    Provides full explainability — every point in the risk score
    can be traced back to a specific rule and condition.
    """

    __tablename__ = "rule_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("analysis_reports.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chemical_identity_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("chemical_identities.id", ondelete="SET NULL"),
        default=None,
    )
    substance_name: Mapped[str] = mapped_column(String(500), nullable=False)
    rule_id: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # e.g., "R001", "R030"
    rule_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "known_reproductive_toxin"
    score_contribution: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    rule_reason: Mapped[str | None] = mapped_column(Text, default=None)
    population: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "pregnancy", "fertility", "lactation"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
