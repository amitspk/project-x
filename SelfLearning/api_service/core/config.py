"""Configuration for API Service."""

import os
from pydantic_settings import BaseSettings
from pydantic import Field


class APIServiceConfig(BaseSettings):
    """API Service configuration."""
    
    # Service
    service_name: str = "api-service"
    service_port: int = Field(default=8005, env="API_SERVICE_PORT")
    
    # MongoDB
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_username: str = Field(default="admin", env="MONGODB_USERNAME")
    mongodb_password: str = Field(default="password123", env="MONGODB_PASSWORD")
    database_name: str = Field(default="blog_qa_db", env="DATABASE_NAME")
    
    # OpenAI
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    
    # Security
    admin_api_key: str = Field(default="", env="ADMIN_API_KEY")
    
    # CORS
    cors_origins: list = Field(default=["*"])
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_config() -> APIServiceConfig:
    """Get configuration instance."""
    return APIServiceConfig()

