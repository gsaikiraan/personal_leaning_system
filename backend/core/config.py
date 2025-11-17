"""
Core configuration management using Pydantic Settings
"""
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "Personal Learning Agent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = Field(..., min_length=32)

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "learning_agent"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = Field(..., min_length=8)
    DATABASE_URL: Optional[str] = None

    @field_validator('DATABASE_URL', mode='before')
    @classmethod
    def assemble_db_url(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        values = info.data
        return (
            f"postgresql+asyncpg://{values.get('POSTGRES_USER')}:"
            f"{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_HOST')}:"
            f"{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
        )

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = Field(..., min_length=8)

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "learning_content"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None

    @field_validator('REDIS_URL', mode='before')
    @classmethod
    def assemble_redis_url(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        values = info.data
        password_part = f":{values.get('REDIS_PASSWORD')}@" if values.get('REDIS_PASSWORD') else ""
        return (
            f"redis://{password_part}{values.get('REDIS_HOST')}:"
            f"{values.get('REDIS_PORT')}/{values.get('REDIS_DB')}"
        )

    # InfluxDB
    INFLUXDB_URL: str = "http://localhost:8086"
    INFLUXDB_TOKEN: str = Field(..., min_length=16)
    INFLUXDB_ORG: str = "learning-org"
    INFLUXDB_BUCKET: str = "user-metrics"

    # Pinecone
    PINECONE_API_KEY: str = Field(..., min_length=20)
    PINECONE_ENVIRONMENT: str = "us-west1-gcp"
    PINECONE_INDEX_NAME: str = "learning-content"

    # Weaviate
    WEAVIATE_URL: str = "http://localhost:8080"
    WEAVIATE_API_KEY: str = ""

    # LLM APIs
    OPENAI_API_KEY: str = Field(..., min_length=20)
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None

    # LangSmith
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "personal-learning-agent"

    # External APIs
    YOUTUBE_API_KEY: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
