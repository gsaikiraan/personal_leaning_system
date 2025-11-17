"""
Database initialization script
Initializes all databases and creates necessary schemas
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.database import (
    init_databases,
    neo4j_conn,
    mongodb_conn,
    redis_conn,
    influxdb_conn
)
from backend.db.neo4j_schema import initialize_knowledge_graph
from backend.core.config import settings


async def main():
    """Main initialization function"""

    print("🚀 Starting database initialization...")
    print(f"Environment: {settings.ENVIRONMENT}")

    try:
        # Initialize all databases
        print("\n📦 Initializing databases...")
        await init_databases()

        # Initialize Neo4j knowledge graph
        print("\n🧠 Initializing knowledge graph...")
        async with await neo4j_conn.get_session() as session:
            await initialize_knowledge_graph(session)

        # Verify connections
        print("\n✅ Verifying connections...")

        # Test PostgreSQL
        from backend.db.database import engine
        from sqlalchemy import text
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✓ PostgreSQL connected")

        # Test Neo4j
        async with await neo4j_conn.get_session() as session:
            result = await session.run("RETURN 1")
            await result.single()
            print("✓ Neo4j connected")

        # Test MongoDB
        await mongodb_conn.db.command('ping')
        print("✓ MongoDB connected")

        # Test Redis
        await redis_conn.redis.ping()
        print("✓ Redis connected")

        # Test InfluxDB
        health = await influxdb_conn.client.ping()
        print("✓ InfluxDB connected")

        print("\n✅ All databases initialized successfully!")
        print("\n📋 Next steps:")
        print("1. Start the backend: cd backend && uvicorn main:app --reload")
        print("2. Visit API docs: http://localhost:8000/api/docs")
        print("3. Create a user account and start learning!")

    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
