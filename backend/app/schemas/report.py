"""Report schemas (Pydantic v2) — response models for report endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SubstanceItem(BaseModel):
    """A single hazardous substance as it appears in a report."""

    id: int
    substance_name: str
    category: str | None = None
    pregnancy_risk: str | None = None
    fertility_risk: str | None = None
    lactation_risk: str | None = None
    risk_reason: str | None = None
    effects_on_fetus: str | None = None
    effects_on_reproduction: str | None = None
    effects_on_breastfeeding: str | None = None
    exposure_routes: list[str] | None = None
    recommended_ppe: str | None = None
    recommended_precautions: str | None = None
    found_in_section: str | None = None


class ExecutiveSummary(BaseModel):
    """Report executive summary with counts and summary text."""

    total_substances_found: int
    high_risk_count: int
    moderate_risk_count: int
    low_risk_count: int
    safe_count: int
    summary_text: str


class RiskByCategory(BaseModel):
    """Risk distribution counts for a single population."""

    high: int = 0
    moderate: int = 0
    low: int = 0
    safe: int = 0


class HighRiskItem(BaseModel):
    """A high-risk substance requiring immediate attention."""

    substance_name: str
    category: str
    pregnancy_risk: str
    fertility_risk: str
    lactation_risk: str
    recommended_precautions: str | None = None


class PrecautionItem(BaseModel):
    """Precaution recommendations for a specific substance."""

    substance_name: str
    risk: str
    precautions: list[str] = Field(default_factory=list)


class ReportDetail(BaseModel):
    """Full structured risk assessment report."""

    id: int
    original_filename: str
    overall_risk: str | None = None
    overall_score: int | None = None
    executive_summary: ExecutiveSummary | None = None
    identified_hazardous_materials: list[SubstanceItem] = Field(default_factory=list)
    high_risk_items: list[HighRiskItem] = Field(default_factory=list)
    recommended_precautions: list[PrecautionItem] = Field(default_factory=list)
    risk_by_category: dict[str, RiskByCategory] | None = None
    disclaimer: str = Field(
        default="本报告仅供实验室安全参考，不能替代职业健康专家建议。使用前请咨询您的医生或职业健康顾问。"
    )
    created_at: datetime | None = None


class SubstanceSearchResult(BaseModel):
    """A single result from the substance search endpoint."""

    id: int
    chemical_name: str
    cas_number: str | None = None
    category: str
    pregnancy_risk: str
    fertility_risk: str
    lactation_risk: str
    ghs_classification: str | None = None
    hazard_statements: str | None = None
    effects_on_fetus: str | None = None
    effects_on_reproduction: str | None = None
    effects_on_breastfeeding: str | None = None
    recommended_ppe: str | None = None
    recommended_precautions: str | None = None
    references: str | None = None


class SubstanceSearchResponse(BaseModel):
    """Paginated substance search response."""

    total: int
    items: list[SubstanceSearchResult]


class ReportListItem(BaseModel):
    """A single item in the report history list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_type: str
    overall_risk: str | None = None
    overall_score: int | None = None
    status: str
    created_at: datetime | None = None


class ReportListResponse(BaseModel):
    """Paginated report history listing."""

    total: int
    page: int
    page_size: int
    items: list[ReportListItem]


class FeedbackRequest(BaseModel):
    """User feedback on a risk assessment."""

    report_id: int
    substance_name: str
    feedback_type: str = Field(..., description="agree / disagree / correction / comment")
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    id: int
    message: str = "Thank you for your feedback."
