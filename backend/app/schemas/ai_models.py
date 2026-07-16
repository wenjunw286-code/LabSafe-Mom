"""Pydantic models for OpenAI Structured Output.

These schemas are used to enforce JSON schema compliance from AI responses,
eliminating the need for regex-based markdown parsing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedSubstance(BaseModel):
    """A single chemical substance extracted from a protocol by AI."""

    name: str = Field(..., description="Substance name (English preferred, e.g., Formaldehyde)")
    category: str = Field(
        ...,
        description="Category: 化学试剂/生物试剂/染料/固定液/有机溶剂/抗生素/放射性物质/麻醉剂/其他",
    )
    found_in_section: str = Field(
        ...,
        description="Original context quoted from the protocol (max 200 characters)",
        max_length=200,
    )


class HazardousStep(BaseModel):
    """A hazardous protocol step identified by AI."""

    description: str = Field(..., description="Description of the hazardous step")
    hazards: list[str] = Field(default_factory=list, description="List of potential hazards")


class ChemicalExtractionResult(BaseModel):
    """Structured output from the chemical extraction AI call."""

    substances: list[ExtractedSubstance] = Field(
        default_factory=list,
        description="Identified hazardous substances in the protocol",
    )
    hazardous_steps: list[HazardousStep] = Field(
        default_factory=list,
        description="Identified hazardous protocol steps",
    )

    @property
    def substance_names(self) -> list[str]:
        """Return flat list of extracted substance names for batch matching."""
        return [s.name for s in self.substances if s.name]


class RiskAssessment(BaseModel):
    """AI-generated risk assessment for a single substance against three populations."""

    substance_name: str = Field(..., description="Name of the assessed substance")
    category: str = Field(default="其他", description="Substance category")
    pregnancy_risk: str = Field(
        default="Unknown",
        description="Risk for pregnancy: Safe/Low Risk/Moderate Risk/High Risk/Unknown",
    )
    fertility_risk: str = Field(
        default="Unknown",
        description="Risk for fertility/trying to conceive: Safe/Low Risk/Moderate Risk/High Risk/Unknown",
    )
    lactation_risk: str = Field(
        default="Unknown",
        description="Risk for breastfeeding: Safe/Low Risk/Moderate Risk/High Risk/Unknown",
    )
    risk_reason: str = Field(
        default="",
        description="Detailed reason for risk assessment (Chinese, max 100 chars)",
        max_length=100,
    )
    effects_on_fetus: str = Field(default="", description="Potential effects on the fetus (Chinese)")
    effects_on_reproduction: str = Field(default="", description="Potential effects on reproduction (Chinese)")
    effects_on_breastfeeding: str = Field(default="", description="Potential effects on breastfeeding (Chinese)")
    exposure_routes: list[str] = Field(
        default_factory=lambda: ["吸入", "皮肤接触"],
        description="Exposure routes: 吸入/皮肤接触/误食/注射/气溶胶",
    )
    recommended_ppe: str = Field(default="", description="Recommended personal protective equipment (Chinese)")
    recommended_precautions: str = Field(
        default="",
        description="Detailed precautions, one per line starting with ✓ (Chinese)",
    )
    found_in_section: str = Field(default="", description="Where in the protocol this was found")
    from_database: bool = Field(default=False, description="Whether this came from the local risk DB")
