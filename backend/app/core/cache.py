"""In-process async TTL cache for read-only upstream market data.

Single-process (one uvicorn worker) so the cache is globally consistent; a 60s TTL
collapses upstream calls to ~1 per key per TTL regardless of user count. Features:
get-or-fetch with per-key single-flight (no stampede on a cold key), serve-stale on
upstream error, and structured hit/miss/stale logging. Swap for Redis only when
running multiple workers/instances.
"""
import asyncio
import time
from typing import Any, Awaitable, Callable

from app.core.observability import log_event


class _Entry:
    """Wraps a cached value with a wall-clock fetch timestamp for freshness reporting."""
    __slots__ = ("value", "fetched_at")

    def __init__(self, value: Any, fetched_at: float) -> None:
        self.value = value
        self.fetched_at = fetched_at   # time.time() at the moment of upstream fetch


class TTLCache:
    def __init__(self, maxsize: int = 512):
        self._store: dict[str, tuple[float, _Entry]] = {}      # key -> (expires_at, entry)
        self._locks: dict[str, asyncio.Lock] = {}
        self._maxsize = maxsize

    async def get_or_fetch(self, key: str, ttl: int, fetch: Callable[[], Awaitable], *, fn: str = ""):
        entry = self._store.get(key)
        if entry and entry[0] > time.monotonic():
            log_event("cache.hit", fn=fn, key=key)
            return entry[1].value

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            # Re-check: another coroutine may have filled the key while we waited.
            entry = self._store.get(key)
            if entry and entry[0] > time.monotonic():
                log_event("cache.hit", fn=fn, key=key)
                return entry[1].value

            log_event("cache.miss", fn=fn, key=key)
            try:
                value = await fetch()
            except Exception:
                if entry is not None:                          # serve stale on upstream error
                    log_event("cache.stale", fn=fn, key=key)
                    return entry[1].value
                raise
            self._set(key, ttl, value)
            return value

    def fetched_at(self, key: str) -> float | None:
        """Return the wall-clock time (time.time()) when key was last fetched, or None."""
        entry = self._store.get(key)
        return entry[1].fetched_at if entry else None

    def latest_fetch(self, prefix: str) -> float | None:
        """Return the most recent fetched_at across all keys starting with prefix, or None."""
        times = [
            entry.fetched_at
            for key, (_, entry) in self._store.items()
            if key.startswith(prefix)
        ]
        return max(times) if times else None

    def _set(self, key: str, ttl: int, value: object) -> None:
        if key not in self._store and len(self._store) >= self._maxsize:
            self._prune()
        self._store[key] = (time.monotonic() + ttl, _Entry(value, time.time()))

    def _prune(self) -> None:
        now = time.monotonic()
        for k in [k for k, (exp, _) in self._store.items() if exp <= now]:
            self._store.pop(k, None)
            self._locks.pop(k, None)
        while len(self._store) >= self._maxsize:               # still full -> drop arbitrary
            k, _ = self._store.popitem()
            self._locks.pop(k, None)

    def clear(self) -> None:
        self._store.clear()
        self._locks.clear()


# Shared instance for all market-data integrations.
market_cache = TTLCache()
