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
    
    # OpenAI
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file that aren't in the config class


def get_config() -> WorkerServiceConfig:
    """Get configuration instance."""
    return WorkerServiceConfig()

