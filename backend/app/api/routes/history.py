"""Report history listing and deletion — async routes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, get_client_id
from app.models.report import AnalysisReport
from app.schemas.report import ReportListItem, ReportListResponse

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: str = Query(default="", description="Filter by status"),
    client_id: str = Depends(get_client_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List the current browser user's analysis reports with pagination.

    Results are ordered by creation date (newest first).
    """
    # Count total
    count_query = select(func.count(AnalysisReport.id)).where(
        AnalysisReport.client_id == client_id
    )
    if status:
        count_query = count_query.where(AnalysisReport.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch page
    query = (
        select(AnalysisReport)
        .where(AnalysisReport.client_id == client_id)
        .order_by(AnalysisReport.created_at.desc())
    )
    if status:
        query = query.where(AnalysisReport.status == status)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    reports = result.scalars().all()

    return ReportListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            ReportListItem(
                id=r.id,
                original_filename=r.original_filename,
                file_type=r.file_type,
                overall_risk=r.overall_risk,
                overall_score=r.overall_score,
                status=r.status,
                created_at=r.created_at,
            )
            for r in reports
        ],
    )


@router.delete("/report/{report_id}")
async def delete_report(
    report_id: int,
    client_id: str = Depends(get_client_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a report and its associated identified substances."""
    result = await db.execute(
        select(AnalysisReport).where(
            AnalysisReport.id == report_id,
            AnalysisReport.client_id == client_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    await db.delete(report)
    await db.commit()

    logger.info("report_deleted", report_id=report_id, client_id=client_id)
    return {"message": "Report deleted", "id": report_id}


@router.delete("/reports")
async def delete_my_reports(
    client_id: str = Depends(get_client_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete all reports owned by the current anonymous browser user."""
    result = await db.execute(
        select(AnalysisReport).where(AnalysisReport.client_id == client_id)
    )
    reports = result.scalars().all()
    deleted = len(reports)
    for report in reports:
        await db.delete(report)
    await db.commit()

    logger.info("reports_deleted", deleted=deleted, client_id=client_id)
    return {"message": "Reports deleted", "deleted": deleted}
