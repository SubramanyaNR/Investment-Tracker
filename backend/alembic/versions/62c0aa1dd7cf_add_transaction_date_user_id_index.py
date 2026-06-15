"""add transaction date user id index

Revision ID: 62c0aa1dd7cf
Revises: a1b2c3d4e5f6
Create Date: 2026-06-15 12:36:02.578041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62c0aa1dd7cf'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_transactions_user_id_transaction_date",
        "transactions",
        ["user_id", "transaction_date"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_transactions_user_id_transaction_date", table_name="transactions")
