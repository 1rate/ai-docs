import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.enums import UserRole
from app.models.user import User


async def main(email: str, password: str, first_name: str, last_name: str) -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == email.lower()))
        user = existing.scalar_one_or_none()
        if user is not None:
            user.role = UserRole.admin
            user.hashed_password = hash_password(password)
            user.first_name = first_name
            user.last_name = last_name or None
            user.is_active = True
            print(f"Updated existing user to admin: {email}")
        else:
            user = User(
                email=email.lower(),
                first_name=first_name,
                last_name=last_name or None,
                hashed_password=hash_password(password),
                role=UserRole.admin,
            )
            db.add(user)
            print(f"Created admin: {email}")
        await db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--first-name", default="Admin")
    parser.add_argument("--last-name", default="")
    args = parser.parse_args()
    asyncio.run(main(args.email, args.password, args.first_name, args.last_name))
