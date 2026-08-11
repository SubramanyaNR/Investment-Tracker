from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

_connect_args = {"ssl": settings.db_ssl} if settings.db_ssl else {}

# Request-path engine: connects as the least-privilege `app_user` role.
engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=_connect_args,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Admin engine: superuser role for the scheduler and migrations (see alembic/env.py).
admin_engine = create_async_engine(
    settings.admin_database_url,
    echo=False,
    connect_args=_connect_args,
)
AdminSessionLocal = async_sessionmaker(admin_engine, expire_on_commit=False)
