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
    
    # PostgreSQL (required)
    postgres_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/blog_qa_publishers",
        env="POSTGRES_URL"
    )
    
    # OpenAI model (API keys are read by LLM library from env vars)
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file that aren't in the config class


def get_config() -> WorkerServiceConfig:
    """Get configuration instance."""
    return WorkerServiceConfig()

