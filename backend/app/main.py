"""LabSafe Mom — FastAPI application entry point.

Production-grade setup with:
- Lifespan-based startup/shutdown (replaces deprecated on_event)
- Rate limiting via slowapi (commented out due to Python 3.13 compat issue)
- Structured logging via structlog
- Environment-based CORS configuration
- Async database initialization
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.errors import RateLimitExceeded
# from slowapi.util import get_remote_address

from app.api.routes import analyze, feedback, history, report, upload
from app.config import settings
from app.core.exceptions import LabSafeBaseError
from app.core.logging_config import setup_logging
from app.db.database import check_db_health, close_db, init_db
from app.services.cache_service import ai_cache
from app.db.seed_data import seed_database
from app.db.database import SyncSessionLocal

logger = structlog.get_logger(__name__)


# ── Rate limiter (disabled — Python 3.13 compat) ────────────────
# limiter = Limiter(
#     key_func=get_remote_address,
#     default_limits=[f"{settings.rate_limit.requests_per_minute}/minute"],
#     application_limits=[f"{settings.rate_limit.requests_per_minute}/minute"],
# )


# ── Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: setup on startup, cleanup on shutdown."""
    # Startup
    setup_logging()
    logger.info(
        "app_starting",
        environment=settings.environment,
        log_format=settings.log_format,
        cache_enabled=settings.cache.enabled,
        rate_limit=settings.rate_limit.requests_per_minute,
    )

    # Initialize database tables
    await init_db()
    logger.info("database_initialized")

    # Seed hazard data if empty
    db = SyncSessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    # Log configuration
    if not settings.openai_api_key or settings.openai_api_key == "sk-placeholder":
        logger.warning("openai_api_key_not_set")
    if settings.debug:
        logger.info("debug_mode_enabled")

    yield  # Application runs here

    # Shutdown
    logger.info("app_shutting_down")
    await close_db()
    ai_cache.clear()
    logger.info("app_shutdown_complete")


# ── Application ───────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="Laboratory Safety Risk Assessment for Expecting Researchers",
    version=settings.app_version,
    lifespan=lifespan,
)

# Rate limiting (disabled — Python 3.13 compat)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(analyze.router, prefix="/api/v1", tags=["Analyze"])
app.include_router(report.router, prefix="/api/v1", tags=["Report"])
app.include_router(history.router, prefix="/api/v1", tags=["History"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])


# ── Error handlers ────────────────────────────────────────────
@app.exception_handler(LabSafeBaseError)
async def labsafe_error_handler(request: Request, exc: LabSafeBaseError) -> JSONResponse:
    """Convert LabSafeBaseError subclasses to structured JSON error responses."""
    status_map: dict[type, int] = {
        type(None): 500,  # fallback
    }
    from app.core.exceptions import (
        FileValidationError,
        FileParsingError,
        ReportNotFoundError,
        ReportNotReadyError,
        RateLimitExceededError,
        AIServiceUnavailableError,
    )
    status_map[FileValidationError] = 400
    status_map[FileParsingError] = 422
    status_map[ReportNotFoundError] = 404
    status_map[ReportNotReadyError] = 400
    status_map[RateLimitExceededError] = 429
    status_map[AIServiceUnavailableError] = 503

    status_code = status_map.get(type(exc), 500)
    logger.warning("app_error", type=type(exc).__name__, message=exc.message, status=status_code)
    return JSONResponse(status_code=status_code, content=exc.to_dict())


# ── Health check ──────────────────────────────────────────────
@app.get("/api/v1/health")
async def health_check():
    """Health check with database connectivity status and cache stats."""
    db_status = await check_db_health()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": db_status,
        "cache": ai_cache.stats,
    }
