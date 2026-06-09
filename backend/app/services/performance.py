"""Performance ranking service — F9 (monthly) + F10 (daily).

Computes best and worst performing assets by % change over a period.
Restricted to CRYPTO and MUTUAL_FUND — FI and MANUAL assets have no
market-driven daily price movement and are excluded.

Monthly (F9): latest vs earliest valuation_history row in the current
  calendar month. No scheduler change needed — data exists if the user
  has recalculated prices at least once this month.

Daily (F10): today's vs yesterday's valuation_history row per asset.
  Requires the nightly recalculate job (also F10) to write daily rows.
  Returns empty results gracefully when yesterday's rows are absent.
"""
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Asset, ValuationHistory

_LIVE_TYPES = ("CRYPTO", "MUTUAL_FUND")
_TOP_N = 3


# ── Result type ─────────────────────────────────────────────────────────────

@dataclass
class PerformanceEntry:
    asset_id:    str
    asset_name:  str
    asset_type:  str
    pct_change:  float          # e.g. 6.3 for +6.3%
    start_value: float
    end_value:   float

    def to_dict(self) -> dict:
        return {
            "asset_id":   self.asset_id,
            "asset_name": self.asset_name,
            "asset_type": self.asset_type,
            "pct_change": round(self.pct_change, 2),
            "start_value": self.start_value,
            "end_value":   self.end_value,
        }


# ── Shared helpers ───────────────────────────────────────────────────────────

def _rank(entries: list[PerformanceEntry]) -> tuple[list[dict], list[dict]]:
    """Return (top, bottom) ranked by pct_change, with no asset in both.

    With >= 2×_TOP_N assets: clean top _TOP_N and bottom _TOP_N.
    With fewer: partition the sorted list down the middle so best performers
    go to top and worst to bottom without overlap (e.g. 2 assets → 1 top,
    1 bottom; 1 asset → top only). Bottom is always worst-first.
    """
    if not entries:
        return [], []
    ranked = sorted(entries, key=lambda e: e.pct_change, reverse=True)

    if len(ranked) >= 2 * _TOP_N:
        top    = [e.to_dict() for e in ranked[:_TOP_N]]
        bottom = [e.to_dict() for e in ranked[-_TOP_N:][::-1]]   # worst first
    else:
        split  = (len(ranked) + 1) // 2          # odd count gives the extra to top
        top    = [e.to_dict() for e in ranked[:split]]
        bottom = [e.to_dict() for e in ranked[split:][::-1]]     # worst first

    return top, bottom


async def _fetch_valuations_for_dates(
    session: AsyncSession,
    user_id: uuid.UUID,
    target_dates: set[date],
) -> dict[tuple[str, date], tuple[float, Optional[float]]]:
    """Return {(asset_id_str, date): (current_value, price_per_unit)} for given dates.

    price_per_unit is None for rows written before the column was added.
    """
    if not target_dates:
        return {}
    result = await session.execute(
        select(
            ValuationHistory.asset_id,
            ValuationHistory.valuation_date,
            ValuationHistory.current_value,
            ValuationHistory.price_per_unit,
        )
        .join(Asset, Asset.id == ValuationHistory.asset_id)
        .where(
            and_(
                ValuationHistory.user_id == user_id,
                ValuationHistory.valuation_date.in_(target_dates),
                Asset.asset_type.in_(_LIVE_TYPES),
            )
        )
    )
    return {
        (str(row[0]), row[1]): (
            float(row[2]),
            float(row[3]) if row[3] is not None else None,
        )
        for row in result.all()
    }


# ── Monthly (F9) ─────────────────────────────────────────────────────────────

async def monthly_performance(session: AsyncSession, user_id: uuid.UUID) -> dict:
    """Top/bottom 3 performers for the current calendar month."""
    today = date.today()
    month_start = date(today.year, today.month, 1)

    # Get min + max valuation date per asset within the current month
    date_bounds = await session.execute(
        select(
            ValuationHistory.asset_id,
            func.min(ValuationHistory.valuation_date).label("first_date"),
            func.max(ValuationHistory.valuation_date).label("last_date"),
        )
        .join(Asset, Asset.id == ValuationHistory.asset_id)
        .where(
            and_(
                ValuationHistory.user_id == user_id,
                ValuationHistory.valuation_date >= month_start,
                ValuationHistory.valuation_date <= today,
                Asset.asset_type.in_(_LIVE_TYPES),
            )
        )
        .group_by(ValuationHistory.asset_id)
    )
    bounds = date_bounds.all()

    if not bounds:
        return {
            "top": [], "bottom": [], "has_data": False,
            "period": "monthly",
            "period_label": today.strftime("%b %Y"),
        }

    # Collect all unique dates we need, then fetch in two targeted queries
    first_dates = {(str(row[0]), row[1]) for row in bounds}
    last_dates  = {(str(row[0]), row[2]) for row in bounds}

    all_target_dates = {row[1] for row in bounds} | {row[2] for row in bounds}
    val_map = await _fetch_valuations_for_dates(session, user_id, all_target_dates)

    # Fetch asset names
    asset_ids = [row[0] for row in bounds]
    asset_result = await session.execute(
        select(Asset.id, Asset.name, Asset.asset_type)
        .where(and_(Asset.user_id == user_id, Asset.id.in_(asset_ids)))
    )
    asset_meta = {str(row[0]): (row[1], row[2]) for row in asset_result.all()}

    entries: list[PerformanceEntry] = []
    for row in bounds:
        aid      = str(row[0])
        first_dt = row[1]
        last_dt  = row[2]
        if first_dt == last_dt:
            continue   # only one data point this month — skip

        start_row = val_map.get((aid, first_dt))
        end_row   = val_map.get((aid, last_dt))
        if not start_row or not end_row:
            continue

        start_cv, start_ppu = start_row
        end_cv,   end_ppu   = end_row

        # Prefer price_per_unit (pure market return, unaffected by position size changes).
        # Fall back to current_value for rows written before the column was added.
        if start_ppu is not None and end_ppu is not None and start_ppu != 0:
            pct = (end_ppu - start_ppu) / start_ppu * 100
        elif start_cv and end_cv and start_cv != 0:
            pct = (end_cv - start_cv) / start_cv * 100
        else:
            continue

        name, atype = asset_meta.get(aid, ("Unknown", "CRYPTO"))
        entries.append(PerformanceEntry(aid, name, atype, pct, start_cv, end_cv))

    top, bottom = _rank(entries)
    return {
        "top": top,
        "bottom": bottom,
        "has_data": bool(entries),
        "period": "monthly",
        "period_label": today.strftime("%b %Y"),
    }


# ── Daily (F10) ──────────────────────────────────────────────────────────────

async def daily_performance(session: AsyncSession, user_id: uuid.UUID) -> dict:
    """Top/bottom 3 performers vs yesterday.

    Returns has_data=False gracefully when yesterday's rows don't exist
    (e.g. the nightly recalculate job has not yet run for this user).
    """
    today     = date.today()
    yesterday = today - timedelta(days=1)

    val_map = await _fetch_valuations_for_dates(session, user_id, {today, yesterday})

    # Find assets that have rows for both days
    today_assets = {aid for (aid, d) in val_map if d == today}
    yest_assets  = {aid for (aid, d) in val_map if d == yesterday}
    both_days    = today_assets & yest_assets


    if not both_days:
        return {
            "top": [], "bottom": [], "has_data": False,
            "period": "daily",
            "period_label": today.isoformat(),
        }

    asset_result = await session.execute(
        select(Asset.id, Asset.name, Asset.asset_type)
        .where(
            and_(
                Asset.user_id == user_id,
                Asset.id.in_([uuid.UUID(aid) for aid in both_days]),
                Asset.asset_type.in_(_LIVE_TYPES),
            )
        )
    )
    asset_meta = {str(row[0]): (row[1], row[2]) for row in asset_result.all()}

    entries: list[PerformanceEntry] = []
    for aid in both_days:
        if aid not in asset_meta:
            continue
        yest_row  = val_map.get((aid, yesterday))
        today_row = val_map.get((aid, today))
        if not yest_row or not today_row:
            continue

        yest_cv,  yest_ppu  = yest_row
        today_cv, today_ppu = today_row

        # Prefer price_per_unit (pure market return, unaffected by position size changes).
        # Fall back to current_value for rows written before the column was added.
        if yest_ppu is not None and today_ppu is not None and yest_ppu != 0:
            pct = (today_ppu - yest_ppu) / yest_ppu * 100
        elif yest_cv and today_cv and yest_cv != 0:
            pct = (today_cv - yest_cv) / yest_cv * 100
        else:
            continue

        name, atype = asset_meta[aid]
        entries.append(PerformanceEntry(aid, name, atype, pct, yest_cv, today_cv))

    top, bottom = _rank(entries)
    return {
        "top": top,
        "bottom": bottom,
        "has_data": bool(entries),
        "period": "daily",
        "period_label": today.isoformat(),
    }
