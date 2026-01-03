"""Configuration for Worker Service."""

from pydantic_settings import BaseSettings
from pydantic import Field


class WorkerServiceConfig(BaseSettings):
    """Worker Service configuration."""
    
    # Service
    service_name: str = "worker-service"
    poll_interval_seconds: int = Field(default=5, env="POLL_INTERVAL_SECONDS")
    concurrent_jobs: int = Field(default=1, env="CONCURRENT_JOBS")
    metrics_port: int = Field(default=8006, env="METRICS_PORT")
    
    # Batch Processing (V3 Optimization)
    batch_size: int = Field(
        default=10,
        env="BATCH_SIZE",
        description="Number of blogs to pick per batch (default: 10)"
    )
    concurrent_processing_limit: int = Field(
        default=5,
        env="CONCURRENT_PROCESSING_LIMIT",
        description="Max number of blogs to process concurrently in a group (default: 5)"
    )
    llm_rate_limit: int = Field(
        default=5,
        env="LLM_RATE_LIMIT",
        description="Max concurrent LLM API calls (default: 5)"
    )
    
    # MongoDB
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_username: str = Field(default="admin", env="MONGODB_USERNAME")
    mongodb_password: str = Field(default="password123", env="MONGODB_PASSWORD")
    database_name: str = Field(default="blog_qa_db", env="DATABASE_NAME")
    
    # MongoDB Connection Pool
    mongodb_max_pool_size: int = Field(default=50, env="MONGODB_MAX_POOL_SIZE", description="Maximum number of connections in MongoDB pool")
    mongodb_min_pool_size: int = Field(default=10, env="MONGODB_MIN_POOL_SIZE", description="Minimum number of connections in MongoDB pool")
    mongodb_max_idle_time_ms: int = Field(default=45000, env="MONGODB_MAX_IDLE_TIME_MS", description="Close idle connections after this many milliseconds")
    mongodb_server_selection_timeout_ms: int = Field(default=5000, env="MONGODB_SERVER_SELECTION_TIMEOUT_MS", description="Timeout for server selection in milliseconds")
    
    # PostgreSQL (required)
    postgres_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/blog_qa_publishers",
        env="POSTGRES_URL"
    )
    
    # PostgreSQL Connection Pool
    postgres_pool_size: int = Field(default=20, env="POSTGRES_POOL_SIZE", description="Base number of connections in PostgreSQL pool")
    postgres_max_overflow: int = Field(default=30, env="POSTGRES_MAX_OVERFLOW", description="Maximum overflow connections beyond pool_size")
    postgres_pool_recycle: int = Field(default=3600, env="POSTGRES_POOL_RECYCLE", description="Recycle connections after this many seconds")
    
    # OpenAI model (API keys are read by LLM library from env vars)
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file that aren't in the config class


def get_config() -> WorkerServiceConfig:
    """Get configuration instance."""
    return WorkerServiceConfig()

