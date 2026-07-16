"""User feedback collection route — async."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db
from app.schemas.report import FeedbackRequest, FeedbackResponse

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Submit user feedback on a risk assessment.

    Feedback is logged for future database improvement.
    A dedicated feedback table can be added in future iterations.
    """
    logger.info(
        "feedback_received",
        report_id=feedback.report_id,
        substance=feedback.substance_name,
        type=feedback.feedback_type,
        comment=feedback.comment,
    )

    # In a full implementation, persist to a feedback table
    # For now, structured logging provides an audit trail

    return FeedbackResponse(
        id=feedback.report_id,
        message="Thank you for your feedback. It will help improve our risk assessments.",
    )
