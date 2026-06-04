from sqlalchemy import event, text
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

_connect_args = {"ssl": settings.db_ssl} if settings.db_ssl else {}

# Request-path engine: connects as the non-superuser `app_user` role, which is
# subject to Row-Level Security. Tenant scoping is enforced here as a backstop.
engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=_connect_args,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Admin engine: superuser role (BYPASSRLS) for the scheduler, which must operate
# across all tenants. Migrations use this role too (see alembic/env.py).
admin_engine = create_async_engine(
    settings.admin_database_url,
    echo=False,
    connect_args=_connect_args,
)
AdminSessionLocal = async_sessionmaker(admin_engine, expire_on_commit=False)


@event.listens_for(SyncSession, "after_begin")
def _apply_rls_user(session, transaction, connection):
    """Set the per-request RLS GUC at the start of every app-engine transaction.

    LOCAL scope auto-clears at commit and never leaks across pooled connections;
    re-applying it on each BEGIN keeps it set across mid-request commits. Sessions
    on the admin engine (and a missing user_id) skip it and thus see no rows under
    RLS — fail closed.
    """
    if connection.engine is not engine.sync_engine:
        return
    user_id = session.info.get("user_id")
    if user_id is not None:
        connection.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )
