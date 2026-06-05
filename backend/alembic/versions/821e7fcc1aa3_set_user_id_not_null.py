"""set user_id not null

Revision ID: 821e7fcc1aa3
Revises: e5cb1f1e7714
Create Date: 2026-06-03 16:51:37.552439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '821e7fcc1aa3'
down_revision: Union[str, Sequence[str], None] = 'e5cb1f1e7714'
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
    for table in _TABLES:
        op.alter_column(table, "user_id", existing_type=sa.UUID(), nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    for table in _TABLES:
        op.alter_column(table, "user_id", existing_type=sa.UUID(), nullable=True)
