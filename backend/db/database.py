"""
Database connection management
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from neo4j import AsyncGraphDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

from backend.core.config import settings


# PostgreSQL (SQLAlchemy Async)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Neo4j Connection
class Neo4jConnection:
    """Neo4j database connection manager"""

    def __init__(self):
        self.driver = None

    async def connect(self):
        """Initialize Neo4j connection"""
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        # Verify connectivity
        await self.driver.verify_connectivity()

    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()

    async def get_session(self):
        """Get Neo4j session"""
        if not self.driver:
            await self.connect()
        return self.driver.session()


neo4j_conn = Neo4jConnection()


async def get_neo4j():
    """Dependency for getting Neo4j session"""
    session = await neo4j_conn.get_session()
    try:
        yield session
    finally:
        await session.close()


# MongoDB Connection
class MongoDBConnection:
    """MongoDB connection manager"""

    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.db = None

    async def connect(self):
        """Initialize MongoDB connection"""
        self.client = AsyncIOMotorClient(settings.MONGODB_URI)
        self.db = self.client[settings.MONGODB_DB]
        # Verify connection
        await self.client.admin.command('ping')

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()

    def get_collection(self, collection_name: str):
        """Get MongoDB collection"""
        if not self.db:
            raise RuntimeError("MongoDB not connected")
        return self.db[collection_name]


mongodb_conn = MongoDBConnection()


async def get_mongodb():
    """Dependency for getting MongoDB database"""
    if not mongodb_conn.db:
        await mongodb_conn.connect()
    return mongodb_conn.db


# Redis Connection
class RedisConnection:
    """Redis connection manager"""

    def __init__(self):
        self.redis: Redis = None

    async def connect(self):
        """Initialize Redis connection"""
        self.redis = Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        # Verify connection
        await self.redis.ping()

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()

    def get_client(self) -> Redis:
        """Get Redis client"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        return self.redis


redis_conn = RedisConnection()


async def get_redis():
    """Dependency for getting Redis client"""
    if not redis_conn.redis:
        await redis_conn.connect()
    return redis_conn.redis


# InfluxDB Connection
class InfluxDBConnection:
    """InfluxDB connection manager"""

    def __init__(self):
        self.client: InfluxDBClientAsync = None
        self.write_api = None
        self.query_api = None

    async def connect(self):
        """Initialize InfluxDB connection"""
        self.client = InfluxDBClientAsync(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN,
            org=settings.INFLUXDB_ORG
        )
        self.write_api = self.client.write_api()
        self.query_api = self.client.query_api()

        # Verify connection
        ready = await self.client.ready()
        if not ready:
            raise RuntimeError("InfluxDB not ready")

    async def close(self):
        """Close InfluxDB connection"""
        if self.client:
            await self.client.close()

    def get_write_api(self):
        """Get InfluxDB write API"""
        if not self.write_api:
            raise RuntimeError("InfluxDB not connected")
        return self.write_api

    def get_query_api(self):
        """Get InfluxDB query API"""
        if not self.query_api:
            raise RuntimeError("InfluxDB not connected")
        return self.query_api


influxdb_conn = InfluxDBConnection()


async def get_influxdb():
    """Dependency for getting InfluxDB client"""
    if not influxdb_conn.client:
        await influxdb_conn.connect()
    return influxdb_conn.client


# Database initialization
async def init_databases():
    """Initialize all database connections"""
    try:
        # PostgreSQL
        async with engine.begin() as conn:
            from backend.db.models import Base
            # Don't create tables automatically in production
            if settings.DEBUG:
                await conn.run_sync(Base.metadata.create_all)

        # Neo4j
        await neo4j_conn.connect()

        # MongoDB
        await mongodb_conn.connect()

        # Create indexes
        await create_mongodb_indexes()

        # Redis
        await redis_conn.connect()

        # InfluxDB
        await influxdb_conn.connect()

        print("✅ All databases initialized successfully")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


async def create_mongodb_indexes():
    """Create MongoDB indexes for better query performance"""
    db = mongodb_conn.db

    # Learning content collection
    content_collection = db.learning_content
    await content_collection.create_index([("topic", 1)])
    await content_collection.create_index([("difficulty", 1)])
    await content_collection.create_index([("source", 1)])
    await content_collection.create_index([("embedding", "vector")])  # Vector search

    # Practice problems collection
    problems_collection = db.practice_problems
    await problems_collection.create_index([("topic", 1)])
    await problems_collection.create_index([("difficulty", 1)])
    await problems_collection.create_index([("type", 1)])

    # Session transcripts collection
    transcripts_collection = db.session_transcripts
    await transcripts_collection.create_index([("user_id", 1), ("created_at", -1)])

    print("✅ MongoDB indexes created")


async def close_databases():
    """Close all database connections"""
    await neo4j_conn.close()
    await mongodb_conn.close()
    await redis_conn.close()
    await influxdb_conn.close()
    await engine.dispose()
    print("✅ All database connections closed")
