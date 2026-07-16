"""FastAPI dependency injection container.

Provides reusable dependencies for all route modules.
Each dependency is a callable suitable for use with `Depends()`.
Services are singletons — created once and reused across requests.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.services.file_parser import FileParser


# ── Database ──────────────────────────────────────────────────


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, auto-committing or rolling back."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Stateless Services ────────────────────────────────────────


def get_file_parser() -> FileParser:
    """Return a FileParser instance (stateless)."""
    return FileParser()


# ── V3 Pipeline Services (created per-request where needed) ──
# The v3 pipeline services require db sessions at construction time,
# so they are instantiated inside the route handlers rather than as
# singletons. The analyze route's _run_analysis_v3() creates them
# directly with its own db session.
