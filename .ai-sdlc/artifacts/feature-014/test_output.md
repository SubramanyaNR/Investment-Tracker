## Pytest Results (exit code: 0)

```
........................................................................ [ 34%]
........................................................................ [ 68%]
..................................................................       [100%]
=============================== warnings summary ===============================
app/core/config.py:4
  /opt/investment-tracker/backend/app/core/config.py:4: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class Settings(BaseSettings):

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
210 passed, 9 warnings in 31.58s
```
