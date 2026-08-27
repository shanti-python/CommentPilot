import asyncio
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import verify_password, get_password_hash
from sqlalchemy import select

async def main():
    async with SessionLocal() as db:
        stmt = select(User)
        res = await db.execute(stmt)
        users = res.scalars().all()
        print(f"--- ALL REGISTERED USERS (Count: {len(users)}) ---")
        for u in users:
            print(f"ID: {u.id} | Email: {u.email} | Is Active: {u.is_active} | Is Superuser: {u.is_superuser}")
            # Test if password Manjesh@123 matches
            hashed = u.hashed_password
            matches = verify_password("Manjesh@123", hashed)
            print(f"Hashed Password: {hashed}")
            print(f"Matches 'Manjesh@123': {matches}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
