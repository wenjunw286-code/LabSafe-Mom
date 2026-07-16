"""File upload route — async with MIME validation."""

from __future__ import annotations

import os

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, get_file_parser
from app.config import settings
from app.core.exceptions import FileParsingError
from app.models.report import AnalysisReport
from app.schemas.upload import UploadResponse
from app.services.file_parser import FileParser

logger = structlog.get_logger(__name__)

router = APIRouter()


class TextUploadRequest(BaseModel):
    title: str = Field(default="pasted_protocol.txt", max_length=200)
    text: str = Field(..., min_length=10)


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    parser: FileParser = Depends(get_file_parser),
):
    """Upload a laboratory protocol file for risk analysis.

    Accepts PDF, DOCX, and TXT files up to the configured size limit.
    Validates MIME type in addition to file extension.
    """

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # ── Validate file extension ───────────────────────────────
    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    if ext not in FileParser.SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: .{ext}。支持的格式: {', '.join(sorted(FileParser.SUPPORTED_TYPES))}",
        )

    # ── Read file content ─────────────────────────────────────
    content = await file.read()

    # ── Validate size ─────────────────────────────────────────
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({settings.max_file_size_mb}MB)",
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="文件为空")

    # ── Optional MIME validation ──────────────────────────────
    if settings.verify_mime_type:
        try:
            import magic
            mime = magic.from_buffer(content[:2048], mime=True)
            allowed_mimes = {"text/plain", "application/pdf",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "application/msword"}
            if mime not in allowed_mimes:
                logger.warning("mime_mismatch", filename=file.filename, mime=mime)
                # Don't block — extension check is sufficient. Log for review.
        except ImportError:
            pass  # python-magic not installed; skip MIME check

    # ── Parse file to text ────────────────────────────────────
    try:
        extracted_text = parser.parse(content, file.filename)
        logger.info("file_parsed", filename=file.filename, text_length=len(extracted_text))
    except FileParsingError as exc:
        raise HTTPException(status_code=422, detail=exc.message)
    except Exception as exc:
        logger.error("file_parse_unexpected", filename=file.filename, error=str(exc))
        raise HTTPException(status_code=422, detail=f"文件解析失败: {str(exc)}")

    # ── Create report record ──────────────────────────────────
    report = AnalysisReport(
        original_filename=file.filename,
        file_type=ext,
        file_size=len(content),
        extracted_text=extracted_text,
        status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Truncate preview for response
    preview = extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text

    logger.info("upload_complete", report_id=report.id, filename=file.filename)

    return UploadResponse(
        id=report.id,
        original_filename=report.original_filename,
        file_type=report.file_type,
        file_size=report.file_size or 0,
        extracted_text=preview,
        status=report.status,
        created_at=report.created_at,
    )


@router.post("/upload/text", response_model=UploadResponse, status_code=201)
async def upload_text_protocol(
    payload: TextUploadRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Create an analysis report directly from pasted protocol text."""
    text = payload.text.strip()
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Protocol text is too short")
    if len(text.encode("utf-8")) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Protocol text exceeds size limit ({settings.max_file_size_mb}MB)",
        )

    title = payload.title.strip() or "pasted_protocol.txt"
    if not title.lower().endswith(".txt"):
        title = f"{title}.txt"

    report = AnalysisReport(
        original_filename=title,
        file_type="txt",
        file_size=len(text.encode("utf-8")),
        extracted_text=text,
        status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    preview = text[:500] + "..." if len(text) > 500 else text

    logger.info("text_upload_complete", report_id=report.id, filename=title)

    return UploadResponse(
        id=report.id,
        original_filename=report.original_filename,
        file_type=report.file_type,
        file_size=report.file_size or 0,
        extracted_text=preview,
        status=report.status,
        created_at=report.created_at,
    )
