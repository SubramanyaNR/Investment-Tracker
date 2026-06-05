"""In-process async TTL cache for read-only upstream market data.

Single-process (one uvicorn worker) so the cache is globally consistent; a 60s TTL
collapses upstream calls to ~1 per key per TTL regardless of user count. Features:
get-or-fetch with per-key single-flight (no stampede on a cold key), serve-stale on
upstream error, and structured hit/miss/stale logging. Swap for Redis only when
running multiple workers/instances.
"""
import asyncio
import time
from typing import Awaitable, Callable

from app.core.observability import log_event


class TTLCache:
    def __init__(self, maxsize: int = 512):
        self._store: dict[str, tuple[float, object]] = {}      # key -> (expires_at, value)
        self._locks: dict[str, asyncio.Lock] = {}
        self._maxsize = maxsize

    async def get_or_fetch(self, key: str, ttl: int, fetch: Callable[[], Awaitable], *, fn: str = ""):
        entry = self._store.get(key)
        if entry and entry[0] > time.monotonic():
            log_event("cache.hit", fn=fn, key=key)
            return entry[1]

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            # Re-check: another coroutine may have filled the key while we waited.
            entry = self._store.get(key)
            if entry and entry[0] > time.monotonic():
                log_event("cache.hit", fn=fn, key=key)
                return entry[1]

            log_event("cache.miss", fn=fn, key=key)
            try:
                value = await fetch()
            except Exception:
                if entry is not None:                          # serve stale on upstream error
                    log_event("cache.stale", fn=fn, key=key)
                    return entry[1]
                raise
            self._set(key, ttl, value)
            return value

    def _set(self, key: str, ttl: int, value: object) -> None:
        if key not in self._store and len(self._store) >= self._maxsize:
            self._prune()
        self._store[key] = (time.monotonic() + ttl, value)

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
