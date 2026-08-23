"""FastAPI dependency injection container.

Provides reusable dependencies for all route modules.
Each dependency is a callable suitable for use with `Depends()`.
Services are singletons — created once and reused across requests.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
import re

from fastapi import Header, HTTPException
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


def get_client_id(x_client_id: str | None = Header(default=None, alias="X-Client-Id")) -> str:
    """Return the anonymous browser client id used to scope report history."""
    value = (x_client_id or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="Missing X-Client-Id header")
    if len(value) > 128 or not re.fullmatch(r"[A-Za-z0-9._:-]+", value):
        raise HTTPException(status_code=400, detail="Invalid X-Client-Id header")
    return value


# ── V3 Pipeline Services (created per-request where needed) ──
# The v3 pipeline services require db sessions at construction time,
# so they are instantiated inside the route handlers rather than as
# singletons. The analyze route's _run_analysis_v3() creates them
# directly with its own db session.
