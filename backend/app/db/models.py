import uuid
from sqlalchemy import String, Numeric, Date, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    pass


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    asset_type: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    liquidity_tier: Mapped[str] = mapped_column(String, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    transaction_date = mapped_column(Date, nullable=False)
    amount = mapped_column(Numeric(18, 2), nullable=False)
    units = mapped_column(Numeric(24, 8), nullable=True)
    price_per_unit = mapped_column(Numeric(18, 6), nullable=True)


class ValuationHistory(Base):
    __tablename__ = "valuation_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    valuation_date = mapped_column(Date, nullable=False)
    invested_amount = mapped_column(Numeric(18, 2), nullable=False)
    current_value = mapped_column(Numeric(18, 2), nullable=False)
    pnl = mapped_column(Numeric(18, 2), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_date = mapped_column(Date, nullable=False, unique=True)
    total_invested = mapped_column(Numeric(18, 2), nullable=False)
    total_value = mapped_column(Numeric(18, 2), nullable=False)
    total_pnl = mapped_column(Numeric(18, 2), nullable=False)
    allocation = mapped_column(JSON, nullable=False)
    liquidity = mapped_column(JSON, nullable=False)
    metrics = mapped_column(JSON, nullable=False)


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    insight_date = mapped_column(Date, nullable=False)
    observations = mapped_column(JSON, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)


class CryptoHolding(Base):
    __tablename__ = "crypto_holdings"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    coingecko_id: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    quantity = mapped_column(Numeric(24, 10), nullable=False)
    avg_buy_price = mapped_column(Numeric(18, 6), nullable=False)


class FixedIncomeHolding(Base):
    __tablename__ = "fixed_income_holdings"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    principal = mapped_column(Numeric(18, 2), nullable=False)
    annual_rate = mapped_column(Numeric(8, 4), nullable=False)
    start_date = mapped_column(Date, nullable=False)
    maturity_date = mapped_column(Date, nullable=True)
    compounding_frequency: Mapped[str] = mapped_column(String, nullable=False)
