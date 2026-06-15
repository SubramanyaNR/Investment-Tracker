## Pytest Results (exit code: 2)

```
==================================== ERRORS ====================================
_________ ERROR collecting tests/integration/test_assets_pagination.py _________
tests/integration/test_assets_pagination.py:6: in <module>
    USER_P = uuid.UUID("pppppppp-pppp-pppp-pppp-pppppppppppp")
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/root/.pyenv/versions/3.11.9/lib/python3.11/uuid.py:179: in __init__
    int = int_(hex, 16)
          ^^^^^^^^^^^^^
E   ValueError: invalid literal for int() with base 16: 'pppppppppppppppppppppppppppppppp'
=============================== warnings summary ===============================
app/core/config.py:4
  /opt/investment-tracker/backend/app/core/config.py:4: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class Settings(BaseSettings):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
ERROR tests/integration/test_assets_pagination.py - ValueError: invalid liter...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 warning, 1 error in 1.30s
```
