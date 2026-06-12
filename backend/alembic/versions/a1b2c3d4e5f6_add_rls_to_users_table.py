"""add RLS to users table

Revision ID: a1b2c3d4e5f6
Revises: 8dcb4a0b4e27
Create Date: 2026-06-12
"""
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = '8dcb4a0b4e27'
branch_labels = None
depends_on = None

_USING = "id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"

def upgrade() -> None:
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON users FOR ALL "
        f"USING ({_USING}) WITH CHECK ({_USING})"
    )

def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
