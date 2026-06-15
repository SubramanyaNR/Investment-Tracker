## Pytest Results (exit code: 1)

```
................................................................F....... [ 35%]
........................................................................ [ 70%]
............................................................             [100%]
=================================== FAILURES ===================================
_____________________ test_models_have_no_migration_drift ______________________
tests/integration/test_migration_drift.py:25: in test_models_have_no_migration_drift
    assert r.returncode == 0, f"model/migration drift detected:\n{r.stdout}\n{r.stderr}"
E   AssertionError: model/migration drift detected:
E     FAILED: New upgrade operations detected: [('remove_index', Index('ix_transactions_user_id_transaction_date', Column('user_id', UUID(), table=<transactions>, nullable=False), Column('transaction_date', DATE(), table=<transactions>, nullable=False)))]
E     
E     INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
E     INFO  [alembic.runtime.migration] Will assume transactional DDL.
E     INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.schemas
E     INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.tables
E     INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.types
E     INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.constraints
E     INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.defaults
E     INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.comments
E     INFO  [alembic.autogenerate.compare.constraints] Detected removed index 'ix_transactions_user_id_transaction_date' on 'transactions'
E     ERROR [alembic.util.messaging] New upgrade operations detected: [('remove_index', Index('ix_transactions_user_id_transaction_date', Column('user_id', UUID(), table=<transactions>, nullable=False), Column('transaction_date', DATE(), table=<transactions>, nullable=False)))]
E     
E   assert 255 == 0
E    +  where 255 = CompletedProcess(args=['/opt/investment-tracker/backend/.venv/bin/python', '-m', 'alembic', 'check'], returncode=255, ... table=<transactions>, nullable=False), Column('transaction_date', DATE(), table=<transactions>, nullable=False)))]\n").returncode
=============================== warnings summary ===============================
app/core/config.py:4
  /opt/investment-tracker/backend/app/core/config.py:4: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class Settings(BaseSettings):

tests/integration/test_asset_merge.py::test_sequential_crypto_add_merges
  /opt/investment-tracker/backend/app/main.py:63: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

tests/integration/test_asset_merge.py::test_sequential_crypto_add_merges
  /opt/investment-tracker/backend/.venv/lib/python3.11/site-packages/fastapi/applications.py:4598: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)  # ty: ignore[deprecated]

tests/integration/test_auth_jwt.py::test_valid_token_accepted
tests/integration/test_auth_jwt.py::test_expired_token_rejected
tests/integration/test_auth_jwt.py::test_wrong_audience_rejected
tests/integration/test_auth_jwt.py::test_wrong_issuer_rejected
tests/integration/test_auth_jwt.py::test_missing_sub_rejected
tests/integration/test_auth_jwt.py::test_missing_exp_rejected
tests/integration/test_auth_jwt.py::test_non_uuid_sub_rejected
  /opt/investment-tracker/backend/.venv/lib/python3.11/site-packages/jwt/api_jwt.py:147: InsecureKeyLengthWarning: The HMAC key is 11 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
    return self._jws.encode(

tests/integration/test_auth_jwt.py::test_alg_hs256_rejected
  /opt/investment-tracker/backend/.venv/lib/python3.11/site-packages/jwt/api_jwt.py:147: InsecureKeyLengthWarning: The HMAC key is 6 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
    return self._jws.encode(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/test_migration_drift.py::test_models_have_no_migration_drift
1 failed, 203 passed, 11 warnings in 22.04s
```
