"""
Configuration settings for the blog manager microservice.

Handles environment variables, database settings, and application configuration.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application Settings
    app_name: str = "Blog Manager Microservice"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # API Settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    
    # MongoDB Settings
    mongodb_host: str = Field(default="localhost", env="MONGODB_HOST")
    mongodb_port: int = Field(default=27017, env="MONGODB_PORT")
    mongodb_username: str = Field(default="admin", env="MONGODB_USERNAME")
    mongodb_password: str = Field(default="password123", env="MONGODB_PASSWORD")
    mongodb_database: str = Field(default="blog_ai_db", env="MONGODB_DATABASE")
    mongodb_auth_source: str = Field(default="admin", env="MONGODB_AUTH_SOURCE")
    
    # Connection Pool Settings
    mongodb_max_pool_size: int = Field(default=100, env="MONGODB_MAX_POOL_SIZE")
    mongodb_min_pool_size: int = Field(default=0, env="MONGODB_MIN_POOL_SIZE")
    mongodb_server_selection_timeout_ms: int = Field(default=10000, env="MONGODB_SERVER_SELECTION_TIMEOUT_MS")
    
    # Cache Settings
    enable_cache: bool = Field(default=True, env="ENABLE_CACHE")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")  # 1 hour
    
    # Logging Settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")
    
    # CORS Settings
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    cors_methods: list = Field(default=["GET", "POST", "PUT", "DELETE"], env="CORS_METHODS")
    cors_headers: list = Field(default=["*"], env="CORS_HEADERS")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # Microservices URLs (2-service architecture)
    content_service_url: str = Field(default="http://localhost:8005", env="CONTENT_SERVICE_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }
    
    @property
    def mongodb_url(self) -> str:
        """Generate MongoDB connection URL."""
        if self.mongodb_username and self.mongodb_password:
            return (
                f"mongodb://{self.mongodb_username}:{self.mongodb_password}@"
                f"{self.mongodb_host}:{self.mongodb_port}/{self.mongodb_auth_source}"
            )
        return f"mongodb://{self.mongodb_host}:{self.mongodb_port}"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.debug


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance for dependency injection."""
    return settings
