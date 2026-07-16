"""TTL-based in-memory cache for AI risk assessment responses.

Eliminates redundant LLM calls for the same substance/category combination.
Thread-safe, bounded size, with automatic eviction of stale entries.
"""

from __future__ import annotations

import hashlib
import threading
import time
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class AICache:
    """Simple TTL cache for AI response objects, keyed by (substance_name, category)."""

    def __init__(self, ttl_seconds: int | None = None, max_size: int | None = None) -> None:
        self._ttl = ttl_seconds or settings.cache.ttl_seconds
        self._max_size = max_size or settings.cache.max_size
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(substance_name: str, category: str = "") -> str:
        """Generate a deterministic cache key."""
        raw = f"{substance_name.strip().lower()}:{category.strip().lower()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, substance_name: str, category: str = "") -> Any | None:
        """Retrieve a cached AI response if it exists and has not expired.

        Returns None on cache miss or expired entry.
        """
        if not settings.cache.enabled:
            return None

        key = self._make_key(substance_name, category)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None

            timestamp, value = entry
            if time.monotonic() - timestamp > self._ttl:
                del self._store[key]
                self._misses += 1
                return None

            self._hits += 1
            logger.debug("cache_hit", key=key[:12])
            return value

    def set(self, substance_name: str, category: str, value: Any) -> None:
        """Store an AI response in the cache."""
        if not settings.cache.enabled:
            return

        key = self._make_key(substance_name, category)
        with self._lock:
            # Evict oldest entry if at capacity
            if len(self._store) >= self._max_size and key not in self._store:
                oldest_key = min(self._store, key=lambda k: self._store[k][0])
                del self._store[oldest_key]
                logger.debug("cache_evict", key=oldest_key[:12])

            self._store[key] = (time.monotonic(), value)
            logger.debug("cache_set", key=key[:12])

    def invalidate(self, substance_name: str, category: str = "") -> None:
        """Remove a specific entry from the cache."""
        key = self._make_key(substance_name, category)
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all cached entries."""
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict[str, Any]:
        """Return cache statistics for monitoring."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0
            return {
                "size": len(self._store),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": round(hit_rate, 1),
                "ttl_seconds": self._ttl,
                "enabled": settings.cache.enabled,
            }


# ── Global singleton ──────────────────────────────────────────
ai_cache = AICache()
