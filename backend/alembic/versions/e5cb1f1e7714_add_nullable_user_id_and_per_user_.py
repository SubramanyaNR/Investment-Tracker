"""add nullable user_id and per-user snapshot constraint

Revision ID: e5cb1f1e7714
Revises: 10cf88b737b1
Create Date: 2026-06-03 16:28:20.592942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5cb1f1e7714'
down_revision: Union[str, Sequence[str], None] = '10cf88b737b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = (
    "assets",
    "transactions",
    "valuation_history",
    "portfolio_snapshots",
    "ai_insights",
    "crypto_holdings",
    "fixed_income_holdings",
    "mutual_fund_holdings",
)


def upgrade() -> None:
    """Upgrade schema."""
    # Added nullable first so existing rows survive; a later migration backfills
    # and flips these to NOT NULL.
    for table in _TABLES:
        op.add_column(table, sa.Column("user_id", sa.UUID(), nullable=True))
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])

    op.drop_constraint("portfolio_snapshots_snapshot_date_key", "portfolio_snapshots", type_="unique")
    op.create_unique_constraint(
        "uq_snapshot_user_date", "portfolio_snapshots", ["user_id", "snapshot_date"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_snapshot_user_date", "portfolio_snapshots", type_="unique")
    op.create_unique_constraint(
        "portfolio_snapshots_snapshot_date_key", "portfolio_snapshots", ["snapshot_date"]
    )

    for table in _TABLES:
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_column(table, "user_id")
