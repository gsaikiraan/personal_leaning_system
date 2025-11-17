"""
Create a test user for development
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.database import AsyncSessionLocal
from backend.db.models import User, UserRole
from backend.api.auth import get_password_hash


async def create_test_user():
    """Create a test user"""

    async with AsyncSessionLocal() as session:
        # Check if user exists
        from sqlalchemy import select
        query = select(User).where(User.email == "test@example.com")
        result = await session.execute(query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("⚠️  Test user already exists")
            print(f"Email: test@example.com")
            print(f"Username: testuser")
            return

        # Create test user
        test_user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("TestPassword123!"),
            full_name="Test User",
            role=UserRole.USER,
            is_active=True,
            is_verified=True
        )

        session.add(test_user)
        await session.commit()

        print("✅ Test user created successfully!")
        print(f"Email: test@example.com")
        print(f"Username: testuser")
        print(f"Password: TestPassword123!")
        print(f"\nYou can now login at: http://localhost:8000/api/docs")


if __name__ == "__main__":
    asyncio.run(create_test_user())
