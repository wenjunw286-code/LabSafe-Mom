"""HazardousSubstance ORM model — SQLAlchemy 2.0 style.

Represents a known hazardous laboratory substance with
population-specific reproductive risk assessments.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class HazardousSubstance(Base):
    """Pre-loaded hazardous substance with risk data per population group."""

    __tablename__ = "hazardous_substances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chemical_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    cas_number: Mapped[str | None] = mapped_column(String(50), index=True, default=None)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Risk levels per population (enum values stored as strings)
    pregnancy_risk: Mapped[str] = mapped_column(String(20), nullable=False, default="Unknown")
    fertility_risk: Mapped[str] = mapped_column(String(20), nullable=False, default="Unknown")
    lactation_risk: Mapped[str] = mapped_column(String(20), nullable=False, default="Unknown")

    # GHS classification
    ghs_classification: Mapped[str | None] = mapped_column(Text, default=None)
    hazard_statements: Mapped[str | None] = mapped_column(Text, default=None)
    exposure_routes: Mapped[list[str]] = mapped_column(
        JSON, default=lambda: ["吸入", "皮肤接触"]
    )

    # Effects per population
    effects_on_fetus: Mapped[str | None] = mapped_column(Text, default=None)
    effects_on_reproduction: Mapped[str | None] = mapped_column(Text, default=None)
    effects_on_breastfeeding: Mapped[str | None] = mapped_column(Text, default=None)

    # Safety recommendations
    recommended_ppe: Mapped[str | None] = mapped_column(Text, default=None)
    recommended_precautions: Mapped[str | None] = mapped_column(Text, default=None)

    # Metadata
    references: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_risk_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for risk assessment output."""
        return {
            "substance_name": self.chemical_name,
            "category": self.category,
            "pregnancy_risk": self.pregnancy_risk,
            "fertility_risk": self.fertility_risk,
            "lactation_risk": self.lactation_risk,
            "risk_reason": f"来自本地风险数据库（CAS: {self.cas_number or 'N/A'}）",
            "effects_on_fetus": self.effects_on_fetus or "",
            "effects_on_reproduction": self.effects_on_reproduction or "",
            "effects_on_breastfeeding": self.effects_on_breastfeeding or "",
            "exposure_routes": self.exposure_routes or [],
            "recommended_ppe": self.recommended_ppe or "",
            "recommended_precautions": self.recommended_precautions or "",
            "from_database": True,
        }
