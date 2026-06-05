"""child-asset user_id consistency constraints

Revision ID: 509c02fff358
Revises: 6a8bdc1bb742
Create Date: 2026-06-03 21:03:11.325119

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '509c02fff358'
down_revision: Union[str, Sequence[str], None] = '6a8bdc1bb742'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Asset-linked child tables (those carrying both asset_id and user_id).
_CHILDREN = (
    "transactions",
    "valuation_history",
    "crypto_holdings",
    "fixed_income_holdings",
    "mutual_fund_holdings",
)


def upgrade() -> None:
    # Composite FK target: guarantees a child row's (asset_id, user_id) pair
    # matches its asset, so a row can never be attributed to the wrong tenant.
    op.create_unique_constraint("uq_assets_id_user", "assets", ["id", "user_id"])
    for t in _CHILDREN:
        op.create_foreign_key(
            f"fk_{t}_asset_user",
            t,
            "assets",
            ["asset_id", "user_id"],
            ["id", "user_id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    for t in _CHILDREN:
        op.drop_constraint(f"fk_{t}_asset_user", t, type_="foreignkey")
    op.drop_constraint("uq_assets_id_user", "assets", type_="unique")
