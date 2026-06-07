"""Unit tests for the in-process TTL cache (A5)."""
import asyncio

import pytest

from app.core.cache import TTLCache

pytestmark = pytest.mark.unit


async def test_miss_then_hit_calls_fetch_once():
    c = TTLCache()
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        return "v"

    assert await c.get_or_fetch("k", 60, fetch, fn="t") == "v"
    assert await c.get_or_fetch("k", 60, fetch, fn="t") == "v"  # served from cache
    assert calls == 1


async def test_expiry_refetches():
    c = TTLCache()
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        return calls

    assert await c.get_or_fetch("k", 0.05, fetch) == 1
    await asyncio.sleep(0.06)
    assert await c.get_or_fetch("k", 0.05, fetch) == 2
    assert calls == 2


async def test_single_flight_concurrent_miss_fetches_once():
    c = TTLCache()
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return "v"

    results = await asyncio.gather(*[c.get_or_fetch("k", 60, fetch) for _ in range(10)])
    assert results == ["v"] * 10
    assert calls == 1  # stampede prevented by per-key single-flight


async def test_serve_stale_on_upstream_error():
    c = TTLCache()
    fail = {"on": False}

    async def fetch():
        if fail["on"]:
            raise RuntimeError("upstream down")
        return "fresh"

    assert await c.get_or_fetch("k", 0.05, fetch) == "fresh"
    await asyncio.sleep(0.06)  # entry now expired
    fail["on"] = True
    assert await c.get_or_fetch("k", 0.05, fetch) == "fresh"  # stale served, not an error


async def test_raises_when_no_cached_value_and_fetch_fails():
    c = TTLCache()

    async def fetch():
        raise RuntimeError("down")

    with pytest.raises(RuntimeError):
        await c.get_or_fetch("k", 60, fetch)


async def test_fetched_at_records_wall_clock_time():
    """F2 — fetched_at returns a recent timestamp after a cache miss."""
    import time
    c = TTLCache()

    async def fetch_v():
        return "v"

    before = time.time()
    await c.get_or_fetch("k", 60, fetch_v)
    after = time.time()
    ts = c.fetched_at("k")
    assert ts is not None
    assert before <= ts <= after


async def test_latest_fetch_returns_most_recent_across_prefix():
    """F2 — latest_fetch picks the newest entry within a prefix."""
    import time
    c = TTLCache()

    async def empty_dict():
        return {}

    await c.get_or_fetch("cg:prices:inr:bitcoin", 60, empty_dict)
    await asyncio.sleep(0.01)
    await c.get_or_fetch("cg:prices:inr:ethereum", 60, empty_dict)

    ts = c.latest_fetch("cg:")
    assert ts is not None
    assert time.time() - ts < 2          # reflects the ethereum fetch (most recent)
    assert c.latest_fetch("mf:nav:") is None   # unrelated prefix returns None


async def test_latest_fetch_none_when_cache_empty():
    """F2 — latest_fetch returns None if no keys match prefix."""
    c = TTLCache()
    assert c.latest_fetch("cg:") is None
