"""Unit tests for performance ranking logic — F9/F10."""
import pytest
from app.services.performance import PerformanceEntry, _rank

pytestmark = pytest.mark.unit


def entry(name: str, pct: float) -> PerformanceEntry:
    return PerformanceEntry("id-" + name, name, "CRYPTO", pct, 100.0, 100.0 * (1 + pct / 100))


# ── _rank tests ────────────────────────────────────────────────────────────

def test_rank_top3_bottom3():
    """U1 — 6 assets: top 3 highest, bottom 3 lowest, no overlap."""
    entries = [entry(n, p) for n, p in [
        ("A", 10.0), ("B", -5.0), ("C", 3.0),
        ("D", -2.0), ("E", 7.0),  ("F", -8.0),
    ]]
    top, bottom = _rank(entries)
    assert [e["asset_name"] for e in top] == ["A", "E", "C"]
    assert [e["asset_name"] for e in bottom] == ["F", "B", "D"]


def test_rank_fewer_than_3():
    """U2 — Only 2 assets: split into 1 best (top) + 1 worst (bottom)."""
    entries = [entry("A", 5.0), entry("B", -3.0)]
    top, bottom = _rank(entries)
    assert len(top) == 1
    assert len(bottom) == 1
    assert top[0]["asset_name"] == "A"      # best
    assert bottom[0]["asset_name"] == "B"   # worst


def test_rank_no_overlap_when_fewer_than_6():
    """U2b — 4 assets: no asset appears in both top and bottom."""
    entries = [entry(n, p) for n, p in [
        ("A", 8.0), ("B", 4.0), ("C", -2.0), ("D", -6.0),
    ]]
    top, bottom = _rank(entries)
    top_ids    = {e["asset_id"] for e in top}
    bottom_ids = {e["asset_id"] for e in bottom}
    assert top_ids.isdisjoint(bottom_ids)


def test_rank_empty_returns_empty():
    """U3 — No entries → empty top and bottom."""
    top, bottom = _rank([])
    assert top == []
    assert bottom == []


def test_rank_single_asset():
    """U4 — Single asset goes to top only."""
    entries = [entry("A", 5.0)]
    top, bottom = _rank(entries)
    assert len(top) == 1
    assert len(bottom) == 0


def test_rank_pct_change_rounded():
    """U5 — pct_change is rounded to 2 decimal places in output."""
    entries = [entry("A", 6.333333)]
    top, _ = _rank(entries)
    assert top[0]["pct_change"] == 6.33


def test_rank_negative_only():
    """U6 — All negative: top 3 are least negative."""
    entries = [entry(n, p) for n, p in [
        ("A", -1.0), ("B", -5.0), ("C", -3.0),
        ("D", -8.0), ("E", -2.0),
    ]]
    top, bottom = _rank(entries)
    # Top = least negative
    assert top[0]["asset_name"] == "A"
    # Bottom = most negative
    assert bottom[0]["asset_name"] == "D"
