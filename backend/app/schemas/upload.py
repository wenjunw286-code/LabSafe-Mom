"""Upload and analysis trigger schemas (Pydantic v2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UploadResponse(BaseModel):
    """Response after a successful file upload."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_type: str
    file_size: int
    extracted_text: str | None = Field(default=None, description="Truncated preview of extracted text")
    status: str
    created_at: datetime


class AnalyzeTriggerResponse(BaseModel):
    """Response when triggering or checking analysis."""

    id: int
    status: str


class AnalyzeStatusResponse(BaseModel):
    """Polling response for analysis progress."""

    id: int
    status: str
    progress: str = Field(default="", description="Human-readable progress description")


class BatchUploadResponse(BaseModel):
    """Response after a batch file upload."""

    uploaded: list[UploadResponse] = Field(default_factory=list)
    failed: list[dict[str, str]] = Field(default_factory=list)
    total_uploaded: int = 0
    total_failed: int = 0
