"""Async database engine and session management.

Uses SQLAlchemy 2.0 with:
- DeclarativeBase (modern style, replacing deprecated declarative_base)
- AsyncEngine for request handling
- Sync engine retained for seed data operations
- Connection pooling configured per environment
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Modern SQLAlchemy 2.0 declarative base class.

    All ORM models inherit from this. Provides:
    - Automatic table name generation from class name
    - Type-safe metadata access
    """

    type_annotation_map: dict[type, Any] = {
        # Add custom type mappings here if needed
    }


# ── Async engine (for request handling) ───────────────────────
def _build_engine_kwargs() -> dict:
    """Build engine kwargs based on database type.

    SQLite (aiosqlite) uses NullPool and doesn't support pool_size/max_overflow.
    PostgreSQL (asyncpg) uses QueuePool with configurable sizing.
    """
    url = settings.database_url
    if "sqlite" in url or "aiosqlite" in url:
        return {
            "echo": settings.debug,
            "connect_args": {"timeout": 30},  # 30s busy timeout to prevent indefinite hangs
        }
    else:
        # PostgreSQL / asyncpg
        return {
            "echo": settings.debug,
            "pool_size": 20 if settings.is_production else 5,
            "max_overflow": 10 if settings.is_production else 2,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }

_async_engine = create_async_engine(settings.database_url, **_build_engine_kwargs())

AsyncSessionLocal = async_sessionmaker(
    _async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent detached instance errors
    autoflush=False,
)

# ── Sync engine (for seed data / migrations) ──────────────────
_sync_engine = create_engine(
    settings.database_url_sync,
    echo=settings.debug,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    _sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async database session.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a sync database session (for legacy operations).

    Prefer `get_async_db` for new code.
    """
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def init_db() -> None:
    """Create all tables. Safe to call multiple times (uses IF NOT EXISTS)."""
    # Ensure all models are imported so they register with Base.metadata
    import app.models  # noqa: F401
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_report_client_id_column)


def _ensure_report_client_id_column(sync_conn) -> None:
    """Add lightweight schema upgrades for deployments without migrations."""
    from sqlalchemy import inspect

    inspector = inspect(sync_conn)
    columns = {column["name"] for column in inspector.get_columns("analysis_reports")}
    if "client_id" not in columns:
        sync_conn.execute(text("ALTER TABLE analysis_reports ADD COLUMN client_id VARCHAR(128)"))
    sync_conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_analysis_reports_client_id ON analysis_reports (client_id)")
    )


async def close_db() -> None:
    """Gracefully dispose of connection pools on shutdown."""
    await _async_engine.dispose()
    _sync_engine.dispose()


async def check_db_health() -> dict[str, str]:
    """Return database health status for health check endpoint."""
    try:
        async with _async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"database": "connected", "url": _redact_db_url(settings.database_url)}
    except Exception as exc:
        return {"database": "disconnected", "error": str(exc)}


def _redact_db_url(url: str) -> str:
    """Remove credentials from database URL for safe logging."""
    import re
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)
