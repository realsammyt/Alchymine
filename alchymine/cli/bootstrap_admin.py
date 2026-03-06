"""Bootstrap the first admin user.

Usage: python -m alchymine.cli.bootstrap_admin

Reads ADMIN_EMAIL from environment and grants admin privileges to that user.
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select, update

from alchymine.db.base import get_async_engine, get_async_session_factory
from alchymine.db.models import User


async def bootstrap() -> None:
    email = os.environ.get("ADMIN_EMAIL", "")
    if not email:
        print("ERROR: ADMIN_EMAIL environment variable is not set.")
        sys.exit(1)

    engine = get_async_engine()
    session_factory = get_async_session_factory(engine)

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            print(f"ERROR: No user found with email '{email}'.")
            await engine.dispose()
            sys.exit(1)

        if user.is_admin:
            print(f"User '{email}' is already an admin.")
            await engine.dispose()
            return

        await session.execute(update(User).where(User.id == user.id).values(is_admin=True))
        await session.commit()
        print(f"SUCCESS: User '{email}' is now an admin.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(bootstrap())
