"""Configuration for API Service."""

import json
from typing import Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class APIServiceConfig(BaseSettings):
    """API Service configuration."""
    
    # Service
    service_name: str = "api-service"
    service_port: int = Field(default=8005, env="API_SERVICE_PORT")
    
    # MongoDB (required)
    mongodb_url: str = Field(..., env="MONGODB_URL")
    mongodb_username: str = Field(..., env="MONGODB_USERNAME")
    mongodb_password: str = Field(..., env="MONGODB_PASSWORD")
    database_name: str = Field(..., env="DATABASE_NAME")
    
    # MongoDB Connection Pool
    mongodb_max_pool_size: int = Field(default=50, env="MONGODB_MAX_POOL_SIZE", description="Maximum number of connections in MongoDB pool")
    mongodb_min_pool_size: int = Field(default=10, env="MONGODB_MIN_POOL_SIZE", description="Minimum number of connections in MongoDB pool")
    mongodb_max_idle_time_ms: int = Field(default=45000, env="MONGODB_MAX_IDLE_TIME_MS", description="Close idle connections after this many milliseconds")
    mongodb_server_selection_timeout_ms: int = Field(default=5000, env="MONGODB_SERVER_SELECTION_TIMEOUT_MS", description="Timeout for server selection in milliseconds")

    # PostgreSQL (required)
    postgres_url: str = Field(..., env="POSTGRES_URL")
    
    # PostgreSQL Connection Pool
    postgres_pool_size: int = Field(default=10, env="POSTGRES_POOL_SIZE", description="Base number of connections in PostgreSQL pool")
    postgres_max_overflow: int = Field(default=20, env="POSTGRES_MAX_OVERFLOW", description="Maximum overflow connections beyond pool_size")
    postgres_pool_recycle: int = Field(default=3600, env="POSTGRES_POOL_RECYCLE", description="Recycle connections after this many seconds")
    
    # OpenAI model (API keys are read by LLM library from env vars)
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    
    # Security (required)
    admin_api_key: str = Field(..., env="ADMIN_API_KEY")
    
    # CORS
    # Accept JSON array string, comma-separated string, or list
    # Examples: '["*"]', 'http://127.0.0.1:5173,http://localhost:5173', or ["*"]
    cors_origins: str = Field(default="*")
    
    @field_validator("cors_origins", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list[str]:
        """Parse CORS_ORIGINS from various formats."""
        if not v or not v.strip():
            return ["*"]
        
        v = v.strip()
        
        # Try to parse as JSON array first
        if v.startswith("["):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    # Filter out empty strings
                    result = [origin.strip() for origin in parsed if origin and origin.strip()]
                    return result if result else ["*"]
            except json.JSONDecodeError:
                pass
        
        # If not JSON, treat as comma-separated string
        if "," in v:
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
            return origins if origins else ["*"]
        
        # Single value
        if v == "*" or v == '["*"]':
            return ["*"]
        
        return [v] if v else ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file that aren't in the config class


def get_config() -> APIServiceConfig:
    """Get configuration instance."""
    return APIServiceConfig()

