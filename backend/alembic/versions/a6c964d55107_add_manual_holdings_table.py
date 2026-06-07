"""add manual_holdings table

Revision ID: a6c964d55107
Revises: f448b186cdf1
Create Date: 2026-06-07 14:10:43.535160

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6c964d55107'
down_revision: Union[str, Sequence[str], None] = 'f448b186cdf1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_USING = "user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('manual_holdings',
    sa.Column('asset_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('cost_basis', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('current_value', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('value_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['asset_id', 'user_id'], ['assets.id', 'assets.user_id'], name='fk_manual_holdings_asset_user', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('asset_id')
    )
    op.create_index(op.f('ix_manual_holdings_user_id'), 'manual_holdings', ['user_id'], unique=False)

    # RLS: same tenant-isolation policy as all other holding tables.
    op.execute("ALTER TABLE manual_holdings ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON manual_holdings FOR ALL "
        f"USING ({_USING}) WITH CHECK ({_USING})"
    )
    # Grant app_user access if the role exists (safe to run before provisioning).
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN "
        "  GRANT SELECT, INSERT, UPDATE, DELETE ON manual_holdings TO app_user; "
        "END IF; END $$;"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON manual_holdings")
    op.execute("ALTER TABLE manual_holdings DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f('ix_manual_holdings_user_id'), table_name='manual_holdings')
    op.drop_table('manual_holdings')
