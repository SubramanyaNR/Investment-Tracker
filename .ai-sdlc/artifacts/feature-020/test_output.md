## Pytest Results (exit code: 0)

```
........................................................................ [ 33%]
........................................................................ [ 66%]
........................................................................ [100%]
=============================== warnings summary ===============================
app/core/config.py:4
  /opt/Investment-Tracker/backend/app/core/config.py:4: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class Settings(BaseSettings):

tests/integration/test_asset_merge.py::test_sequential_crypto_add_merges
  /opt/Investment-Tracker/backend/.venv/lib/python3.14/site-packages/google/genai/types.py:42: DeprecationWarning: '_UnionGenericAlias' is deprecated and slated for removal in Python 3.17
    VersionedUnionType = Union[builtin_types.UnionType, _UnionGenericAlias]

tests/unit/test_auth.py::test_wrong_secret_401
  /opt/Investment-Tracker/backend/.venv/lib/python3.14/site-packages/jwt/api_jwt.py:147: InsecureKeyLengthWarning: The HMAC key is 29 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
    return self._jws.encode(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
216 passed, 3 warnings in 25.99s
```
