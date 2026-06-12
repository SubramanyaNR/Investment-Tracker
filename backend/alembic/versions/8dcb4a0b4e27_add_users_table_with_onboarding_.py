"""Add users table with onboarding_completed flag

Revision ID: 8dcb4a0b4e27
Revises: ae2fc64ac52f
Create Date: 2026-06-12 08:27:36.760796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8dcb4a0b4e27'
down_revision: Union[str, Sequence[str], None] = 'ae2fc64ac52f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('onboarding_completed', sa.Boolean(), server_default='false', nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Backfill: any user who already has assets is considered to have completed onboarding.
    op.execute("""
        INSERT INTO users (id, onboarding_completed)
        SELECT DISTINCT user_id, true
        FROM assets
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('users')
