## Modified Files (git diff HEAD)

```diff
diff --git a/backend/app/api/auth.py b/backend/app/api/auth.py
index 71c79ca..63de2af 100644
--- a/backend/app/api/auth.py
+++ b/backend/app/api/auth.py
@@ -50,10 +50,26 @@ async def bootstrap_admin_user() -> None:
         session.add(user)
         await session.commit()
         log_event("auth.bootstrap.created_admin", email=settings.admin_email)
 
 
+@router.get("/status")
+async def auth_status():
+    """Public (unauthenticated) — the frontend needs this pre-login to decide
+    whether to show the disabled-auth warning banner. Deliberately not gated:
+    it discloses only whether *this* instance requires a password, no more than
+    the banner itself would already reveal once rendered.
+
+    deployment_context defaults to "hosted" (the stronger warning) when unset —
+    fail-safe, never silently falls back to the milder "local" wording.
+    """
+    return {
+        "auth_enabled": settings.auth_enabled,
+        "deployment_context": settings.deployment_context or "hosted",
+    }
+
+
 @router.post("/login")
 async def login(payload: LoginRequest, request: Request, response: Response):
     ip = client_ip(request)
     allowed, retry = limiter.check(f"login:{ip}", settings.rl_login_attempts)
     if not allowed:
diff --git a/backend/app/core/auth.py b/backend/app/core/auth.py
index 6e686e0..62546b5 100644
--- a/backend/app/core/auth.py
+++ b/backend/app/core/auth.py
@@ -40,11 +40,39 @@ def create_access_token(user_id: uuid.UUID) -> str:
         "exp": now + timedelta(seconds=settings.access_token_ttl_seconds),
     }
     return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
 
 
-def get_current_user_id(access_token: str | None = Cookie(default=None)) -> uuid.UUID:
+_disabled_mode_admin_id: uuid.UUID | None = None
+
+
+async def _resolve_disabled_mode_user_id() -> uuid.UUID:
+    """AUTH_ENABLED=false: every request resolves to the single bootstrapped
+    admin user — never null, never client-supplied. Cached after the first
+    lookup since there is exactly one user row for the life of a single-user
+    deployment; avoids a DB round trip on every request."""
+    global _disabled_mode_admin_id
+    if _disabled_mode_admin_id is not None:
+        return _disabled_mode_admin_id
+
+    # Local imports: core/auth.py otherwise has no DB dependency, and this path
+    # only ever runs when auth is disabled.
+    from sqlalchemy import select
+    from app.db.models import User
+    from app.db.session import AdminSessionLocal
+
+    async with AdminSessionLocal() as session:
+        row = (await session.execute(select(User.id).limit(1))).first()
+    if row is None:
+        raise HTTPException(status_code=500, detail="Auth is disabled but no admin user exists yet")
+    _disabled_mode_admin_id = row[0]
+    return _disabled_mode_admin_id
+
+
+async def get_current_user_id(access_token: str | None = Cookie(default=None)) -> uuid.UUID:
+    if not settings.auth_enabled:
+        return await _resolve_disabled_mode_user_id()
     if access_token is None:
         raise HTTPException(status_code=401, detail="Not authenticated")
     try:
         claims = jwt.decode(
             access_token,
diff --git a/backend/app/core/config.py b/backend/app/core/config.py
index de6ab37..bdd7f2a 100644
--- a/backend/app/core/config.py
+++ b/backend/app/core/config.py
@@ -38,10 +38,21 @@ class Settings(BaseSettings):
     cookie_secure: bool = False
     # Login attempts per IP per window (WINDOW=60s in ratelimit.py) — cheap
     # brute-force insurance now that there's no email-based password reset.
     rl_login_attempts: int = 5
 
+    # ── secure-001 / feature-020: auth-toggle ────────────────────────────────
+    # Off by default (local/self-host convenience) — every request resolves to
+    # the single bootstrapped admin user with no credential check. The frontend
+    # shows a persistent warning whenever this is false; see deployment_context.
+    auth_enabled: bool = False
+    # No safe default — must be set explicitly by the deployer. Only ever
+    # changes the disabled-auth warning's wording (never suppresses it): an
+    # unset/missing value defaults to the strongest ("hosted") copy, fail-safe,
+    # rather than silently falling back to the milder "local" wording.
+    deployment_context: str | None = None
+
     # ── A5: market caching + rate limiting ──────────────────────────────────
     rate_limit_enabled: bool = True
     # Backend binds 127.0.0.1 (reachable only via the proxy), so a proxy-set
     # X-Forwarded-For is trustworthy for client identification.
     trust_forwarded_for: bool = True
diff --git a/backend/tests/conftest.py b/backend/tests/conftest.py
index 43f2cee..eba8841 100644
--- a/backend/tests/conftest.py
+++ b/backend/tests/conftest.py
@@ -14,5 +14,10 @@ import os
 os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
 os.environ.setdefault("ADMIN_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
 os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-a-real-secret")
 os.environ.setdefault("ADMIN_EMAIL", "admin@test.invalid")
 os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password-not-real")
+# AUTH_ENABLED defaults to false in production (secure-001/feature-020), but the
+# suite's existing 401/identity tests assume the credential check is active —
+# opt in explicitly here so the default-off behavior doesn't silently swallow them.
+# Tests for the disabled-auth bypass itself override this per-test.
+os.environ.setdefault("AUTH_ENABLED", "true")
diff --git a/backend/tests/unit/test_auth.py b/backend/tests/unit/test_auth.py
index ac4a567..5ecd375 100644
--- a/backend/tests/unit/test_auth.py
+++ b/backend/tests/unit/test_auth.py
@@ -46,72 +46,72 @@ def test_verify_malformed_hash_fails_closed():
     assert not verify_password("anything", "not-a-real-bcrypt-hash")
 
 
 # ── Access token (HS256) ──────────────────────────────────────────────────────
 
-def _expect_401(token):
+async def _expect_401(token):
     with pytest.raises(HTTPException) as ei:
-        get_current_user_id(access_token=token)
+        await get_current_user_id(access_token=token)
     assert ei.value.status_code == 401
 
 
-def test_valid_access_token_returns_sub():
+async def test_valid_access_token_returns_sub():
     token = create_access_token(VALID_SUB)
-    assert get_current_user_id(access_token=token) == VALID_SUB
+    assert await get_current_user_id(access_token=token) == VALID_SUB
 
 
-def test_missing_cookie_401():
-    _expect_401(None)
+async def test_missing_cookie_401():
+    await _expect_401(None)
 
 
-def test_expired_token_401():
+async def test_expired_token_401():
     now = datetime.datetime.now(UTC)
     claims = {"sub": str(VALID_SUB), "iat": now, "exp": now - datetime.timedelta(seconds=1)}
     token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
-    _expect_401(token)
+    await _expect_401(token)
 
 
-def test_missing_sub_401():
+async def test_missing_sub_401():
     now = datetime.datetime.now(UTC)
     claims = {"iat": now, "exp": now + datetime.timedelta(hours=1)}
     token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
-    _expect_401(token)
+    await _expect_401(token)
 
 
-def test_non_uuid_sub_401():
+async def test_non_uuid_sub_401():
     now = datetime.datetime.now(UTC)
     claims = {"sub": "not-a-uuid", "iat": now, "exp": now + datetime.timedelta(hours=1)}
     token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
-    _expect_401(token)
+    await _expect_401(token)
 
 
-def test_wrong_secret_401():
+async def test_wrong_secret_401():
     now = datetime.datetime.now(UTC)
     claims = {"sub": str(VALID_SUB), "iat": now, "exp": now + datetime.timedelta(hours=1)}
     token = jwt.encode(claims, "a-completely-different-secret", algorithm="HS256")
-    _expect_401(token)
+    await _expect_401(token)
 
 
-def test_alg_none_401():
+async def test_alg_none_401():
     now = datetime.datetime.now(UTC)
     claims = {"sub": str(VALID_SUB), "iat": now, "exp": now + datetime.timedelta(hours=1)}
     token = jwt.encode(claims, "", algorithm="none")
-    _expect_401(token)
+    await _expect_401(token)
 
 
-def test_tampered_payload_401():
+async def test_tampered_payload_401():
     token = create_access_token(VALID_SUB)
     head, payload, sig = token.split(".")
     payload = ("A" if payload[0] != "A" else "B") + payload[1:]
-    _expect_401(f"{head}.{payload}.{sig}")
+    await _expect_401(f"{head}.{payload}.{sig}")
 
 
-def test_malformed_token_401():
-    _expect_401("not.a.valid.jwt")
+async def test_malformed_token_401():
+    await _expect_401("not.a.valid.jwt")
 
 
-def test_old_supabase_style_es256_token_rejected():
+async def test_old_supabase_style_es256_token_rejected():
     """A token from the old Supabase Auth path (ES256, different issuer/audience
     shape) must not be accepted post-cutover — proves the old path is gone, not
     just that a new one was added alongside it."""
     from cryptography.hazmat.primitives.asymmetric import ec
 
@@ -123,11 +123,11 @@ def test_old_supabase_style_es256_token_rejected():
         "aud": "authenticated",
         "iat": now,
         "exp": now + datetime.timedelta(hours=1),
     }
     token = jwt.encode(claims, priv, algorithm="ES256")
-    _expect_401(token)
+    await _expect_401(token)
 
 
 # ── Refresh token ──────────────────────────────────────────────────────────
 
 def test_refresh_token_hash_is_deterministic():
@@ -180,5 +180,99 @@ def test_csrf_mismatched_values_rejected():
     assert ei.value.status_code == 403
 
 
 def test_csrf_matching_values_accepted():
     csrf_check("POST", "/assets", True, "matching-value", "matching-value")  # no raise
+
+
+# ── AUTH_ENABLED=false bypass (secure-001 / feature-020) ────────────────────
+# get_current_user_id must always resolve to the one bootstrapped admin user
+# when auth is disabled — never null, never whatever the caller supplies.
+
+BOOTSTRAPPED_ADMIN = uuid.UUID("99999999-9999-9999-9999-999999999999")
+
+
+class _FakeAdminResult:
+    def __init__(self, row):
+        self._row = row
+
+    def first(self):
+        return self._row
+
+
+class _FakeAdminSession:
+    def __init__(self, row):
+        self._row = row
+
+    async def __aenter__(self):
+        return self
+
+    async def __aexit__(self, *_exc):
+        return False
+
+    async def execute(self, *_args, **_kwargs):
+        return _FakeAdminResult(self._row)
+
+
+@pytest.fixture(autouse=True)
+def _reset_disabled_mode_cache():
+    """The bypass caches the resolved admin id at module scope — reset it around
+    every test in this file so tests don't leak state into each other."""
+    auth_module._disabled_mode_admin_id = None
+    yield
+    auth_module._disabled_mode_admin_id = None
+
+
+def _patch_admin_session(monkeypatch, row):
+    import app.db.session as db_session
+    monkeypatch.setattr(db_session, "AdminSessionLocal", lambda: _FakeAdminSession(row))
+
+
+async def test_auth_disabled_resolves_to_bootstrapped_admin(monkeypatch):
+    monkeypatch.setattr(settings, "auth_enabled", False)
+    _patch_admin_session(monkeypatch, (BOOTSTRAPPED_ADMIN,))
+    assert await get_current_user_id(access_token=None) == BOOTSTRAPPED_ADMIN
+
+
+async def test_auth_disabled_ignores_client_supplied_token(monkeypatch):
+    """A forged/valid-looking cookie claiming a different user must be ignored
+    entirely — the disabled-mode identity always comes from the DB lookup, never
+    from anything the caller sends."""
+    monkeypatch.setattr(settings, "auth_enabled", False)
+    _patch_admin_session(monkeypatch, (BOOTSTRAPPED_ADMIN,))
+    forged = create_access_token(uuid.UUID("22222222-2222-2222-2222-222222222222"))
+    assert await get_current_user_id(access_token=forged) == BOOTSTRAPPED_ADMIN
+
+
+async def test_auth_disabled_no_user_row_raises_500(monkeypatch):
+    monkeypatch.setattr(settings, "auth_enabled", False)
+    _patch_admin_session(monkeypatch, None)
+    with pytest.raises(HTTPException) as ei:
+        await get_current_user_id(access_token=None)
+    assert ei.value.status_code == 500
+
+
+async def test_auth_disabled_caches_after_first_lookup(monkeypatch):
+    monkeypatch.setattr(settings, "auth_enabled", False)
+    calls = {"n": 0}
+
+    class _CountingSession(_FakeAdminSession):
+        async def execute(self, *args, **kwargs):
+            calls["n"] += 1
+            return await super().execute(*args, **kwargs)
+
+    import app.db.session as db_session
+    monkeypatch.setattr(db_session, "AdminSessionLocal", lambda: _CountingSession((BOOTSTRAPPED_ADMIN,)))
+
+    await get_current_user_id(access_token=None)
+    await get_current_user_id(access_token=None)
+    assert calls["n"] == 1
+
+
+async def test_auth_enabled_still_requires_valid_token_when_flag_is_false_elsewhere(monkeypatch):
+    """Sanity check the flag actually gates the branch: with auth_enabled=True
+    (the test-suite default), a missing cookie still 401s exactly as before,
+    even though the disabled-mode code path now exists."""
+    monkeypatch.setattr(settings, "auth_enabled", True)
+    with pytest.raises(HTTPException) as ei:
+        await get_current_user_id(access_token=None)
+    assert ei.value.status_code == 401
diff --git a/frontend/app/layout.tsx b/frontend/app/layout.tsx
index 56d23f4..c591fb0 100644
--- a/frontend/app/layout.tsx
+++ b/frontend/app/layout.tsx
@@ -1,9 +1,10 @@
 import type { Metadata } from "next";
 import "./globals.css";
 import { ThemeProvider } from "@/components/ThemeProvider";
 import { AuthProvider } from "@/components/AuthProvider";
+import AuthDisabledBanner from "@/components/AuthDisabledBanner";
 
 export const metadata: Metadata = {
   title: "Investment Tracker",
   description: "Personal portfolio observability platform",
 };
@@ -25,10 +26,11 @@ export default function RootLayout({ children }: { children: React.ReactNode })
           }}
         />
       </head>
       <body>
         <ThemeProvider>
+          <AuthDisabledBanner />
           <AuthProvider>{children}</AuthProvider>
         </ThemeProvider>
       </body>
     </html>
   );
diff --git a/frontend/lib/api.ts b/frontend/lib/api.ts
index 60bac87..2a7f012 100644
--- a/frontend/lib/api.ts
+++ b/frontend/lib/api.ts
@@ -242,10 +242,19 @@ export async function getMe(): Promise<{ user_id: string } | null> {
 export async function refreshSession(): Promise<boolean> {
   const res = await fetch(`${API_BASE_URL}/auth/refresh`, { method: "POST", headers: csrfHeaders() });
   return res.ok;
 }
 
+export type AuthStatus = { auth_enabled: boolean; deployment_context: "local" | "hosted" };
+
+// Unauthenticated by design — must work pre-login so the disabled-auth banner
+// can render even when there's no session yet.
+export async function getAuthStatus(): Promise<AuthStatus | null> {
+  const res = await fetch(`${API_BASE_URL}/auth/status`, { cache: "no-store" });
+  return res.ok ? res.json() : null;
+}
+
 // ── API functions ──────────────────────────────────────────────────────────
 
 export const getDashboard = () => get<{
   total_value: number;
   total_invested: number;
```

## New File: backend/scripts/__init__.py

```

```

## New File: backend/scripts/reset_admin_password.py

```
"""Reset the single admin user's credentials.

The only supported way to change email/password after first-run bootstrap —
ADMIN_EMAIL/ADMIN_PASSWORD in .env are read once, at the first startup when
`users` is empty, and never again (see bootstrap_admin_user in
app/api/auth.py). Editing .env after that has no effect on the stored row.

CLI-only, deliberately: never expose this logic via an HTTP route. Run via
`make reset-admin-password`.

See docs/runbooks/ADMIN-ACCOUNT-RECOVERY.md.
"""
import asyncio
import getpass
import sys
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.core.auth import hash_password
from app.db.models import RefreshToken, User
from app.db.session import AdminSessionLocal


async def main() -> None:
    async with AdminSessionLocal() as session:
        user = (await session.execute(select(User))).scalars().first()
        if user is None:
            print("No admin user exists yet — start the backend once first "
                  "(bootstrap creates it automatically from ADMIN_EMAIL/ADMIN_PASSWORD).")
            sys.exit(1)

        print(f"Current admin email: {user.email}")
        new_email = input("New email (leave blank to keep current): ").strip()

        new_password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm new password: ")
        if not new_password:
            print("Password cannot be empty — nothing changed.")
            sys.exit(1)
        if new_password != confirm:
            print("Passwords did not match — nothing changed.")
            sys.exit(1)

        user.password_hash = hash_password(new_password)
        if new_email:
            user.email = new_email

        # Revoke every outstanding refresh token so old sessions can't silently
        # renew past their current access token. This only matters once
        # AUTH_ENABLED=true is actually gating requests — with auth disabled
        # there's no session to invalidate, since nothing was checking
        # credentials in the first place.
        now = datetime.now(timezone.utc)
        result = await session.execute(
            update(RefreshToken).where(RefreshToken.revoked_at.is_(None)).values(revoked_at=now)
        )
        await session.commit()
        print(f"Credentials updated. Revoked {result.rowcount} active session(s).")
        print("Note: an already-issued access token remains valid for up to its "
              "15-minute TTL even after this reset — the same as after a normal logout.")


if __name__ == "__main__":
    asyncio.run(main())

```

## New File: frontend/components/AuthDisabledBanner.tsx

```
"use client";

import { useEffect, useState } from "react";
import { getAuthStatus } from "@/lib/api";

// Shows whenever AUTH_ENABLED=false on the backend — regardless of local vs.
// hosted deployment_context (secure-001 R4: no default may silently suppress
// this). deployment_context only changes the wording/severity. Dismissal is
// in-memory only (resets on reload) — never persisted, so it can't be
// silenced permanently by accident.
export default function AuthDisabledBanner() {
  const [status, setStatus] = useState<Awaited<ReturnType<typeof getAuthStatus>>>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    getAuthStatus().then(setStatus);
  }, []);

  if (!status || status.auth_enabled || dismissed) return null;

  const hosted = status.deployment_context === "hosted";

  return (
    <div
      role="alert"
      className={`w-full px-4 py-2 text-sm flex items-center justify-between gap-4 border-b ${
        hosted
          ? "bg-red-500/15 border-red-500/30 text-red-200"
          : "bg-amber-500/15 border-amber-500/30 text-amber-200"
      }`}
    >
      <span>
        <strong>Login is disabled.</strong>{" "}
        {hosted
          ? "Anyone who can reach this address can view and edit your portfolio data. Enable auth (AUTH_ENABLED=true) and run `make reset-admin-password` before exposing this instance."
          : "Anyone with access to this machine can view and edit your portfolio data. Fine for a single local device — if that's no longer true, set AUTH_ENABLED=true, run `make reset-admin-password`, and restart."}
      </span>
      <button
        onClick={() => setDismissed(true)}
        className="shrink-0 opacity-70 hover:opacity-100 transition-opacity"
        aria-label="Dismiss for this session"
      >
        Dismiss
      </button>
    </div>
  );
}

```
