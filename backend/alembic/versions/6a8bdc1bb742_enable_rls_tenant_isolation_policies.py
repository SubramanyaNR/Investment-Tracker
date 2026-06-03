"""enable RLS tenant isolation policies

Revision ID: 6a8bdc1bb742
Revises: 821e7fcc1aa3
Create Date: 2026-06-03 21:03:10.729554

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a8bdc1bb742'
down_revision: Union[str, Sequence[str], None] = '821e7fcc1aa3'
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

# Defense-in-depth backstop: the app connects as the non-superuser `app_user`
# role (no BYPASSRLS) and sets `app.current_user_id` per request. These policies
# make a forgotten WHERE user_id fail closed instead of leaking across tenants.
# NULLIF(...,'') guards against a blank value (the Supabase pooler can leave a
# stale/empty GUC on a reused connection) so the ::uuid cast yields NULL -> deny,
# never an error.
_USING = "user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"


def upgrade() -> None:
    for t in _TABLES:
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {t} FOR ALL "
            f"USING ({_USING}) WITH CHECK ({_USING})"
        )

    # app_user is created out-of-band (cluster role, holds a password); grant only
    # if it exists so this migration is safe to run before the role is provisioned.
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN "
        "  GRANT USAGE ON SCHEMA public TO app_user; "
        "  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user; "
        "  ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user; "
        "END IF; END $$;"
    )


def downgrade() -> None:
    for t in _TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")
        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")
