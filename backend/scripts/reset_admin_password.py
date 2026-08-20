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
