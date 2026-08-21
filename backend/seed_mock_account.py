import asyncio
from app.db.session import SessionLocal
from app.db.repository import instagram_account_repo, post_repo
from sqlalchemy import select
from app.models.user import User
from app.models.instagram import InstagramAccount, Post
from datetime import datetime

async def seed():
    print("Connecting to database...")
    async with SessionLocal() as db:
        # Find default user
        query = select(User).where(User.email == "admin@insta-automator.com")
        res = await db.execute(query)
        user = res.scalars().first()
        if not user:
            print("User admin@insta-automator.com not found. Make sure backend is configured and initialized.")
            return

        print(f"Found User: {user.email} (ID: {user.id})")

        # Check if mock account exists
        existing = await instagram_account_repo.get_by_instagram_id(db, "991122")
        if not existing:
            print("Seeding mock Instagram account @brand_growth...")
            account_data = {
                "user_id": user.id,
                "instagram_business_account_id": "991122",
                "page_id": "page_991122",
                "username": "brand_growth",
                "name": "Brand Growth Sandbox",
                "profile_picture_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80",
                "page_access_token": "mock_page_token",
                "user_access_token": "mock_user_token"
            }
            account = await instagram_account_repo.create(db, obj_in=account_data)
            await db.commit()
            await db.refresh(account)
            print(f"Created Instagram Account ID: {account.id}")
        else:
            account = existing
            print(f"Mock Instagram account already exists with ID: {account.id}")

        # Seed mock posts
        print("Checking mock posts...")
        mock_posts = [
            {
                "id": "media_post_1",
                "instagram_account_id": account.id,
                "caption": "Drop the word 'GUIDE' below to get our 7-day home workout plan! 🏋️‍♂️💪 #homeworkout",
                "media_type": "IMAGE",
                "media_url": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=500&auto=format&fit=crop&q=80",
                "permalink": "https://instagram.com/p/media_post_1",
                "timestamp": datetime.utcnow()
            },
            {
                "id": "media_post_2",
                "instagram_account_id": account.id,
                "caption": "Want 20% off your next order? Comment 'PROMO' and we will DM you a secret discount code! 🏷️",
                "media_type": "IMAGE",
                "media_url": "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=500&auto=format&fit=crop&q=80",
                "permalink": "https://instagram.com/p/media_post_2",
                "timestamp": datetime.utcnow()
            }
        ]

        for mp in mock_posts:
            existing_p = await post_repo.get(db, mp["id"])
            if not existing_p:
                print(f"Creating mock post {mp['id']}...")
                await post_repo.create(db, obj_in=mp)
        
        await db.commit()
        print("Seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
