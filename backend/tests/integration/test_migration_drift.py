"""Drift guard (A8): the SQLAlchemy models must match the migration-produced schema.

Runs `alembic check` against the freshly-migrated container; a non-zero result means
autogenerate would emit operations (e.g. dropping the L2 composite FKs) — fail.
"""
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_models_have_no_migration_drift(pg):
    env = {
        **os.environ,
        "ADMIN_DATABASE_URL": pg["super_url"], "DATABASE_URL": pg["app_url"], "DB_SSL": "",
        "SUPABASE_JWKS_URL": "https://test.invalid/jwks", "SUPABASE_ISSUER": "https://test.invalid",
    }
    r = subprocess.run([sys.executable, "-m", "alembic", "check"], cwd=BACKEND,
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, f"model/migration drift detected:\n{r.stdout}\n{r.stderr}"
