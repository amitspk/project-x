"""Configuration for API Service."""

import os
from pydantic_settings import BaseSettings
from pydantic import Field


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
    
    # OpenAI
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    
    # Security (required)
    admin_api_key: str = Field(..., env="ADMIN_API_KEY")
    
    # CORS
    # Accept a JSON array in CORS_ORIGINS or default to ["*"]
    cors_origins: list[str] = Field(default_factory=lambda: ["*"]) 
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_config() -> APIServiceConfig:
    """Get configuration instance."""
    return APIServiceConfig()

