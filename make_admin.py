"""Make a user an admin — the only way to create the FIRST admin.

Usage:
    uv run python make_admin.py alice@example.com
"""

import asyncio
import sys

from sqlalchemy import select

from src.auth.models import User
from src.database import AsyncSessionLocal


async def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: uv run python make_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1]

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"No user found with email {email!r} — register them first.")
            sys.exit(1)

        user.is_admin = True
        await db.commit()
        print(f"✅ {email} is now an admin.")


asyncio.run(main())