"""XIRR calculation service — F5.

Computes portfolio-level and per-asset XIRR (Internal Rate of Return)
using the Newton-Raphson method over irregular cash flows.

Cash flow convention (XIRR standard):
  BUY / DEPOSIT → negative (money leaves investor's pocket)
  SELL          → positive (money returns to investor)
  Current value → positive terminal cash flow at today's date

XIRR is annualised: a 14.3% XIRR means ₹100 invested grows at 14.3% per year,
accounting for the exact timing and size of every transaction.

Manual assets (asset_type = 'MANUAL') are excluded from all calculations.
They have no transaction history and no auto-valuation, so XIRR is undefined
for them. The response flags manual_assets_excluded when any exist.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Asset, Transaction, ValuationHistory

# ── Solver ─────────────────────────────────────────────────────────────────

_MAX_ITER  = 100
_TOLERANCE = 1e-7
_INITIAL_RATE = 0.10   # 10% starting guess — works for almost all real portfolios


def _newton_raphson(cash_flows: list[tuple[date, float]]) -> Optional[float]:
    """Solve for XIRR using Newton-Raphson iteration.

    cash_flows: [(date, amount)] where negative = outflow, positive = inflow.
    Returns annualised decimal rate (e.g. 0.143 for 14.3%) or None if:
      - fewer than 2 data points
      - all flows have the same sign (no inflow/outflow mix)
      - no convergence within MAX_ITER iterations
    """
    if len(cash_flows) < 2:
        return None

    amounts = [cf[1] for cf in cash_flows]
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        return None

    base = min(cf[0] for cf in cash_flows)
    days = [(cf[0] - base).days for cf in cash_flows]

    rate = _INITIAL_RATE
    for _ in range(_MAX_ITER):
        try:
            npv  = sum(a / (1 + rate) ** (d / 365.0) for a, d in zip(amounts, days))
            dnpv = sum(-d / 365.0 * a / (1 + rate) ** (d / 365.0 + 1) for a, d in zip(amounts, days))
        except (ZeroDivisionError, OverflowError):
            return None

        if abs(dnpv) < 1e-12:
            return None

        new_rate = rate - npv / dnpv

        # Guard against divergence into unphysical territory
        if new_rate <= -1.0 or new_rate > 1000.0:
            return None

        if abs(new_rate - rate) < _TOLERANCE:
            return round(new_rate, 6)

        rate = new_rate

    return None   # no convergence


# ── Cash flow builder ───────────────────────────────────────────────────────

def _build_cash_flows(
    transactions: list[tuple[str, date, float]],   # (tx_type, date, amount)
    current_value: float,
    today: date,
) -> list[tuple[date, float]]:
    """Convert transaction rows and current value into signed XIRR cash flows."""
    flows: list[tuple[date, float]] = []

    for tx_type, tx_date, amount in transactions:
        if tx_type in ("BUY", "DEPOSIT"):
            flows.append((tx_date, -abs(amount)))
        elif tx_type == "SELL":
            flows.append((tx_date, abs(amount)))
        # Unknown types skipped

    if current_value > 0:
        flows.append((today, current_value))

    return flows


# ── Main query + calculation ────────────────────────────────────────────────

async def compute_xirr(session: AsyncSession, user_id: uuid.UUID) -> dict:
    """Compute portfolio-level and per-asset XIRR for a user.

    Returns:
      {
        portfolio_xirr:       float | None,
        portfolio_start_date: str   | None,   # ISO date of earliest transaction
        manual_assets_excluded: bool,
        assets: [
          {
            asset_id:      str,
            asset_name:    str,
            asset_type:    str,
            xirr:          float | None,
            start_date:    str   | None,
            total_invested: float,
            current_value:  float,
          }
        ]
      }
    """
    today = date.today()

    # Check whether any manual assets exist for the caveat flag
    manual_count_row = await session.execute(
        select(func.count()).select_from(Asset).where(
            and_(Asset.user_id == user_id, Asset.asset_type == "MANUAL")
        )
    )
    manual_assets_excluded = (manual_count_row.scalar() or 0) > 0

    # Fetch latest current_value per non-MANUAL asset (via subquery for latest date)
    latest_date_subq = (
        select(
            ValuationHistory.asset_id,
            func.max(ValuationHistory.valuation_date).label("latest_date"),
        )
        .where(ValuationHistory.user_id == user_id)
        .group_by(ValuationHistory.asset_id)
        .subquery()
    )

    val_result = await session.execute(
        select(Asset.id, Asset.name, Asset.asset_type, ValuationHistory.current_value)
        .join(ValuationHistory, ValuationHistory.asset_id == Asset.id)
        .join(
            latest_date_subq,
            and_(
                ValuationHistory.asset_id == latest_date_subq.c.asset_id,
                ValuationHistory.valuation_date == latest_date_subq.c.latest_date,
            ),
        )
        .where(
            and_(
                Asset.user_id == user_id,
                Asset.asset_type != "MANUAL",
            )
        )
    )
    valuation_rows = val_result.all()

    if not valuation_rows:
        return {
            "portfolio_xirr": None,
            "portfolio_start_date": None,
            "manual_assets_excluded": manual_assets_excluded,
            "assets": [],
        }

    # Build asset lookup
    asset_map = {
        str(row[0]): {
            "asset_id":     str(row[0]),
            "asset_name":   row[1],
            "asset_type":   row[2],
            "current_value": float(row[3]),
        }
        for row in valuation_rows
    }
    eligible_asset_ids = list(asset_map.keys())

    # Fetch all transactions for eligible assets
    tx_result = await session.execute(
        select(
            Transaction.asset_id,
            Transaction.transaction_type,
            Transaction.transaction_date,
            Transaction.amount,
        )
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.asset_id.in_([uuid.UUID(aid) for aid in eligible_asset_ids]),
            )
        )
        .order_by(Transaction.transaction_date)
    )
    tx_rows = tx_result.all()

    # Group transactions by asset
    asset_txs: dict[str, list[tuple[str, date, float]]] = {aid: [] for aid in eligible_asset_ids}
    for row in tx_rows:
        aid = str(row[0])
        if aid in asset_txs:
            asset_txs[aid].append((row[1], row[2], float(row[3])))

    # --- Per-asset XIRR ---
    asset_results = []
    all_portfolio_flows: list[tuple[date, float]] = []

    for aid, meta in asset_map.items():
        txs = asset_txs.get(aid, [])
        current_value = meta["current_value"]
        total_invested = sum(abs(a) for t, _, a in txs if t in ("BUY", "DEPOSIT"))

        flows = _build_cash_flows(txs, current_value, today)
        start_date = min(cf[0] for cf in txs if txs) if txs else None
        asset_xirr = _newton_raphson(flows) if flows else None

        asset_results.append({
            "asset_id":      aid,
            "asset_name":    meta["asset_name"],
            "asset_type":    meta["asset_type"],
            "xirr":          asset_xirr,
            "start_date":    str(start_date) if start_date else None,
            "total_invested": total_invested,
            "current_value": current_value,
        })

        # Accumulate portfolio-level flows
        all_portfolio_flows.extend(flows)

    # Sort portfolio flows by date and deduplicate terminal values
    # (each asset already contributed its current_value as a terminal flow above)
    portfolio_flows_no_terminal = []
    for aid, meta in asset_map.items():
        txs = asset_txs.get(aid, [])
        portfolio_flows_no_terminal.extend(_build_cash_flows(txs, 0, today))

    total_current_value = sum(m["current_value"] for m in asset_map.values())
    if total_current_value > 0:
        portfolio_flows_no_terminal.append((today, total_current_value))

    portfolio_xirr = _newton_raphson(portfolio_flows_no_terminal)

    # Portfolio start date = earliest transaction across all assets
    all_tx_dates = [tx[1] for txs in asset_txs.values() for tx in txs]
    portfolio_start_date = min(all_tx_dates) if all_tx_dates else None

    return {
        "portfolio_xirr":       portfolio_xirr,
        "portfolio_start_date": str(portfolio_start_date) if portfolio_start_date else None,
        "manual_assets_excluded": manual_assets_excluded,
        "assets": sorted(asset_results, key=lambda a: a["asset_name"]),
    }
