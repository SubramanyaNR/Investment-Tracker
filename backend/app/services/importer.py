"""CSV transaction import service — F4.

Parses and validates a CSV file of historical transactions, then
executes the import by creating/merging assets and writing transaction rows.
Reuses the same asset-merge semantics as POST /assets (CRYPTO by coingecko_id,
MF by scheme_code). All imported rows carry user_id from the JWT — never from
the CSV itself.

Limits: 500 rows, 100 KB. CSV parsed with stdlib csv only (no formula risk).
"""
import csv
import io
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Asset, CryptoHolding, MutualFundHolding, Transaction, ValuationHistory

# ── Constants ──────────────────────────────────────────────────────────────

ROW_LIMIT   = 500
SIZE_LIMIT  = 100 * 1024  # 100 KB

REQUIRED_COLUMNS = {
    "transaction_date", "asset_type", "asset_name",
    "transaction_type", "amount",
}

OPTIONAL_COLUMNS = {"units", "price_per_unit", "coingecko_id", "scheme_code"}

VALID_ASSET_TYPES = {"CRYPTO", "MUTUAL_FUND", "FD", "RD", "PPF", "SAVINGS_ACC"}
VALID_TX_TYPES    = {"BUY", "SELL", "DEPOSIT"}
FI_TYPES          = {"FD", "RD", "PPF", "SAVINGS_ACC"}

# ── CSV template ───────────────────────────────────────────────────────────

CSV_TEMPLATE = (
    "transaction_date,asset_type,asset_name,transaction_type,"
    "amount,units,price_per_unit,coingecko_id,scheme_code\n"
    "2022-01-15,CRYPTO,Bitcoin,BUY,46000,0.005,9200000,bitcoin,\n"
    "2022-02-01,MUTUAL_FUND,PPFAS Flexi Cap,BUY,5000,12.5,400,,120503\n"
    "2022-03-01,MUTUAL_FUND,PPFAS Flexi Cap,BUY,5000,11.9,420.17,,120503\n"
    "2021-04-10,FD,SBI Fixed Deposit,DEPOSIT,100000,,,, \n"
)

# ── Row model ──────────────────────────────────────────────────────────────

class ImportRow:
    """A fully validated, import-ready row."""
    __slots__ = (
        "row_num", "transaction_date", "asset_type", "asset_name",
        "transaction_type", "amount", "units", "price_per_unit",
        "coingecko_id", "scheme_code",
    )

    def __init__(self, row_num: int, transaction_date: date, asset_type: str,
                 asset_name: str, transaction_type: str, amount: Decimal,
                 units: Optional[Decimal], price_per_unit: Optional[Decimal],
                 coingecko_id: Optional[str], scheme_code: Optional[str]):
        self.row_num          = row_num
        self.transaction_date = transaction_date
        self.asset_type       = asset_type
        self.asset_name       = asset_name
        self.transaction_type = transaction_type
        self.amount           = amount
        self.units            = units
        self.price_per_unit   = price_per_unit
        self.coingecko_id     = coingecko_id
        self.scheme_code      = scheme_code

    def to_preview(self) -> dict:
        return {
            "row_num":          self.row_num,
            "transaction_date": str(self.transaction_date),
            "asset_type":       self.asset_type,
            "asset_name":       self.asset_name,
            "transaction_type": self.transaction_type,
            "amount":           float(self.amount),
            "units":            float(self.units) if self.units else None,
            "price_per_unit":   float(self.price_per_unit) if self.price_per_unit else None,
            "coingecko_id":     self.coingecko_id,
            "scheme_code":      self.scheme_code,
        }


# ── Parsing ────────────────────────────────────────────────────────────────

def parse_and_validate(content: bytes) -> tuple[list[ImportRow], list[dict]]:
    """Parse CSV bytes and validate each row.

    Returns (valid_rows, error_list). Caller decides whether to abort on
    errors or show preview. File-level errors raise ValueError immediately.
    """
    if len(content) > SIZE_LIMIT:
        raise ValueError(f"File exceeds {SIZE_LIMIT // 1024} KB limit")

    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    # Normalise header names (strip whitespace)
    fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]
    missing = REQUIRED_COLUMNS - set(fieldnames)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    raw_rows = list(reader)
    if not raw_rows:
        raise ValueError("CSV contains no data rows (header only)")
    if len(raw_rows) > ROW_LIMIT:
        raise ValueError(f"CSV exceeds {ROW_LIMIT}-row limit ({len(raw_rows)} rows found)")

    valid_rows: list[ImportRow] = []
    errors: list[dict] = []

    for i, raw in enumerate(raw_rows, start=2):          # row 1 is header
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items()}
        errs: list[str] = []

        # ── transaction_date ──
        try:
            tx_date = date.fromisoformat(row.get("transaction_date", ""))
        except ValueError:
            errs.append(f"invalid date '{row.get('transaction_date', '')}' — use YYYY-MM-DD")
            tx_date = None  # type: ignore

        # ── asset_type ──
        asset_type = row.get("asset_type", "").upper()
        if asset_type not in VALID_ASSET_TYPES:
            errs.append(f"invalid asset_type '{asset_type}' — use {' | '.join(sorted(VALID_ASSET_TYPES))}")

        # ── transaction_type ──
        tx_type = row.get("transaction_type", "").upper()
        if tx_type not in VALID_TX_TYPES:
            errs.append(f"invalid transaction_type '{tx_type}' — use BUY | SELL | DEPOSIT")

        # ── asset_name ──
        asset_name = row.get("asset_name", "")
        if not asset_name:
            errs.append("asset_name is required")

        # ── amount ──
        try:
            amount = Decimal(row.get("amount", "").replace(",", ""))
            if amount <= 0:
                errs.append("amount must be greater than zero")
        except InvalidOperation:
            errs.append(f"invalid amount '{row.get('amount', '')}'")
            amount = None  # type: ignore

        # ── units (optional, required for CRYPTO + MF) ──
        units_str = row.get("units", "").replace(",", "")
        units: Optional[Decimal] = None
        if units_str:
            try:
                units = Decimal(units_str)
                if units <= 0:
                    errs.append("units must be greater than zero")
            except InvalidOperation:
                errs.append(f"invalid units '{units_str}'")

        # ── price_per_unit (optional) ──
        ppu_str = row.get("price_per_unit", "").replace(",", "")
        price_per_unit: Optional[Decimal] = None
        if ppu_str:
            try:
                price_per_unit = Decimal(ppu_str)
            except InvalidOperation:
                errs.append(f"invalid price_per_unit '{ppu_str}'")

        # ── coingecko_id (required for CRYPTO) ──
        coingecko_id = row.get("coingecko_id", "").lower() or None
        if asset_type == "CRYPTO":
            if not coingecko_id:
                errs.append("coingecko_id is required for CRYPTO")
            if units is None and not errs:
                errs.append("units is required for CRYPTO")

        # ── scheme_code (required for MF) ──
        scheme_code = row.get("scheme_code", "") or None
        if asset_type == "MUTUAL_FUND":
            if not scheme_code:
                errs.append("scheme_code is required for MUTUAL_FUND")
            if units is None and not errs:
                errs.append("units is required for MUTUAL_FUND")

        if errs:
            errors.append({"row_num": i, "errors": errs,
                           "raw": {k: row.get(k, "") for k in REQUIRED_COLUMNS | OPTIONAL_COLUMNS}})
            continue

        valid_rows.append(ImportRow(
            row_num=i,
            transaction_date=tx_date,      # type: ignore[arg-type]
            asset_type=asset_type,
            asset_name=asset_name,
            transaction_type=tx_type,
            amount=amount,                  # type: ignore[arg-type]
            units=units,
            price_per_unit=price_per_unit,
            coingecko_id=coingecko_id,
            scheme_code=scheme_code,
        ))

    return valid_rows, errors


# ── Import execution ───────────────────────────────────────────────────────

async def execute_import(
    session: AsyncSession,
    user_id: uuid.UUID,
    rows: list[ImportRow],
) -> dict:
    """Write validated rows to the database.

    Creates/merges assets (same semantics as POST /assets) and writes
    one Transaction row per import row. For newly created assets, writes
    an initial valuation_history row (source="import"). Existing asset
    valuations are updated on the next POST /valuations/recalculate.

    Returns a summary dict.
    """
    created_assets = 0
    merged_assets  = 0
    transactions_written = 0

    # Cache asset lookups within this import to avoid N+1 queries.
    # Key: (asset_type, coingecko_id) for CRYPTO, (asset_type, scheme_code) for MF,
    #      (asset_type, asset_name) for FI/others.
    asset_cache: dict[tuple, uuid.UUID] = {}

    for row in rows:
        cache_key = _cache_key(row)
        asset_id  = asset_cache.get(cache_key)

        if asset_id is None:
            asset_id, is_new = await _find_or_create_asset(session, user_id, row)
            asset_cache[cache_key] = asset_id
            if is_new:
                created_assets += 1
                # Write initial valuation row for new asset
                session.add(ValuationHistory(
                    user_id=user_id,
                    asset_id=asset_id,
                    valuation_date=row.transaction_date,
                    invested_amount=row.amount,
                    current_value=row.amount,
                    pnl=Decimal("0"),
                    source="import",
                ))
            else:
                merged_assets += 1

        session.add(Transaction(
            user_id=user_id,
            asset_id=asset_id,
            transaction_type=row.transaction_type,
            transaction_date=row.transaction_date,
            amount=row.amount,
            units=row.units,
            price_per_unit=row.price_per_unit,
        ))
        transactions_written += 1

    await session.commit()
    return {
        "transactions_imported": transactions_written,
        "assets_created":        created_assets,
        "assets_merged":         merged_assets,
    }


# ── Private helpers ────────────────────────────────────────────────────────

def _cache_key(row: ImportRow) -> tuple:
    if row.asset_type == "CRYPTO":
        return ("CRYPTO", row.coingecko_id)
    if row.asset_type == "MUTUAL_FUND":
        return ("MUTUAL_FUND", row.scheme_code)
    return (row.asset_type, row.asset_name)


async def _find_or_create_asset(
    session: AsyncSession,
    user_id: uuid.UUID,
    row: ImportRow,
) -> tuple[uuid.UUID, bool]:
    """Return (asset_id, is_new). Merges CRYPTO/MF into existing holdings."""

    # ── CRYPTO: merge by coingecko_id ──
    if row.asset_type == "CRYPTO":
        result = await session.execute(
            select(CryptoHolding).where(
                and_(CryptoHolding.coingecko_id == row.coingecko_id,
                     CryptoHolding.user_id == user_id)
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if row.transaction_type == "BUY" and row.units:
                old_qty = existing.quantity
                add_qty = row.units
                add_price = row.price_per_unit or (row.amount / add_qty)
                total_qty = old_qty + add_qty
                if total_qty > 0:
                    existing.avg_buy_price = (
                        old_qty * existing.avg_buy_price + add_qty * add_price
                    ) / total_qty
                existing.quantity = total_qty
            return existing.asset_id, False

        asset = Asset(user_id=user_id, name=row.asset_name, asset_type="CRYPTO",
                      category="crypto", liquidity_tier="LIQUID")
        session.add(asset)
        await session.flush()
        symbol = (row.coingecko_id or "").upper()
        session.add(CryptoHolding(
            user_id=user_id, asset_id=asset.id,
            coingecko_id=row.coingecko_id,
            symbol=symbol,
            quantity=row.units or Decimal("0"),
            avg_buy_price=row.price_per_unit or (row.amount / row.units) if row.units else Decimal("0"),
        ))
        return asset.id, True

    # ── MUTUAL_FUND: merge by scheme_code ──
    if row.asset_type == "MUTUAL_FUND":
        result = await session.execute(
            select(MutualFundHolding).where(
                and_(MutualFundHolding.scheme_code == row.scheme_code,
                     MutualFundHolding.user_id == user_id)
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if row.transaction_type == "BUY" and row.units:
                add_units = row.units
                add_nav   = row.price_per_unit or (row.amount / add_units)
                old_units = existing.units
                total_units = old_units + add_units
                if total_units > 0:
                    existing.nav_at_purchase = (
                        old_units * existing.nav_at_purchase + add_units * add_nav
                    ) / total_units
                existing.units = total_units
            return existing.asset_id, False

        add_units = row.units or Decimal("0")
        add_nav   = row.price_per_unit or (row.amount / add_units if add_units else Decimal("0"))
        asset = Asset(user_id=user_id, name=row.asset_name, asset_type="MUTUAL_FUND",
                      category="equity", liquidity_tier="LIQUID")
        session.add(asset)
        await session.flush()
        session.add(MutualFundHolding(
            user_id=user_id, asset_id=asset.id,
            scheme_code=row.scheme_code,
            units=add_units,
            nav_at_purchase=add_nav,
            monthly_sip=None,
        ))
        return asset.id, True

    # ── FI / other: always create new asset ──
    category = "savings" if row.asset_type == "SAVINGS_ACC" else "debt"
    liquidity_tier = "LOCKED" if row.asset_type in {"FD", "PPF"} else "LIQUID"
    asset = Asset(user_id=user_id, name=row.asset_name, asset_type=row.asset_type,
                  category=category, liquidity_tier=liquidity_tier)
    session.add(asset)
    await session.flush()
    return asset.id, True
