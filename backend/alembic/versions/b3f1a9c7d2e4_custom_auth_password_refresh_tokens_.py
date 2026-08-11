"""custom auth: password_hash, refresh_tokens, drop RLS

architecture-002 Phase 2 — replacing Supabase Auth with self-issued bcrypt+JWT.
Single-user model: the multi-tenant RLS backstop (6a8bdc1bb742, a1b2c3d4e5f6) is
removed entirely rather than kept dormant. App-layer WHERE-user_id filtering,
already documented as mandatory, is unchanged and remains the sole enforcement.

Revision ID: b3f1a9c7d2e4
Revises: 62c0aa1dd7cf
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'b3f1a9c7d2e4'
down_revision: Union[str, Sequence[str], None] = '62c0aa1dd7cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Every table RLS was ever enabled on, across all three migrations that added
# policies over time: 6a8bdc1bb742 (original 8), a1b2c3d4e5f6 (users, added
# separately), a6c964d55107 (manual_holdings, added later still — easy to miss).
_RLS_TABLES = (
    "users",
    "assets",
    "transactions",
    "valuation_history",
    "portfolio_snapshots",
    "ai_insights",
    "crypto_holdings",
    "fixed_income_holdings",
    "mutual_fund_holdings",
    "manual_holdings",
)


def upgrade() -> None:
    # email lived entirely in Supabase's own auth.users before this — this table
    # only ever stored the onboarding flag keyed by the Supabase-issued UUID.
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(), nullable=False, server_default=""),
    )
    # server_default was only to satisfy NOT NULL against a (possibly non-empty)
    # existing table; drop it so future inserts must supply a real hash explicitly.
    op.alter_column("users", "password_hash", server_default=None)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    for t in _RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")
        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    _USING_USERS = "id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"
    _USING_OTHERS = "user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"

    for t in _RLS_TABLES:
        using = _USING_USERS if t == "users" else _USING_OTHERS
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {t} FOR ALL "
            f"USING ({using}) WITH CHECK ({using})"
        )

    op.drop_table("refresh_tokens")
    op.drop_column("users", "password_hash")
