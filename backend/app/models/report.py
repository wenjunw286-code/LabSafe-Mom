"""AnalysisReport and IdentifiedSubstance ORM models — SQLAlchemy 2.0 style."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class AnalysisReport(Base):
    """A submitted protocol analysis report."""

    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, default=None)
    extracted_text: Mapped[str | None] = mapped_column(Text, default=None)

    # Analysis results
    overall_risk: Mapped[str | None] = mapped_column(String(20), default=None)
    overall_score: Mapped[int | None] = mapped_column(Integer, default=None)
    report_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    # Lifecycle
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    substances: Mapped[list["IdentifiedSubstance"]] = relationship(
        "IdentifiedSubstance", back_populates="report", cascade="all, delete-orphan"
    )


class IdentifiedSubstance(Base):
    """A substance identified in a specific analysis report."""

    __tablename__ = "identified_substances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_reports.id", ondelete="CASCADE"), index=True
    )
    substance_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("hazardous_substances.id", ondelete="SET NULL"), default=None
    )

    substance_name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), default=None)

    # Risk levels
    pregnancy_risk: Mapped[str | None] = mapped_column(String(20), default=None)
    fertility_risk: Mapped[str | None] = mapped_column(String(20), default=None)
    lactation_risk: Mapped[str | None] = mapped_column(String(20), default=None)

    risk_reason: Mapped[str | None] = mapped_column(Text, default=None)
    effects_on_fetus: Mapped[str | None] = mapped_column(Text, default=None)
    effects_on_reproduction: Mapped[str | None] = mapped_column(Text, default=None)
    effects_on_breastfeeding: Mapped[str | None] = mapped_column(Text, default=None)
    exposure_routes: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    recommended_ppe: Mapped[str | None] = mapped_column(Text, default=None)
    recommended_precautions: Mapped[str | None] = mapped_column(Text, default=None)
    found_in_section: Mapped[str | None] = mapped_column(Text, default=None)
    from_database: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    report: Mapped["AnalysisReport"] = relationship(
        "AnalysisReport", back_populates="substances"
    )
