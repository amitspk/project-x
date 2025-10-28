"""
Configuration for Vector DB Service.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Vector DB Service configuration."""
    
    # MongoDB settings
    mongodb_url: str = os.getenv(
        "MONGODB_URL", 
        "mongodb://localhost:27017"
    )
    mongodb_host: str = os.getenv("MONGODB_HOST", "localhost")
    mongodb_port: int = int(os.getenv("MONGODB_PORT", "27017"))
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "blog_qa_db")
    mongodb_max_pool_size: int = int(os.getenv("MONGODB_MAX_POOL_SIZE", "100"))
    mongodb_min_pool_size: int = int(os.getenv("MONGODB_MIN_POOL_SIZE", "10"))
    mongodb_server_selection_timeout_ms: int = int(
        os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000")
    )
    
    # Service settings
    service_name: str = "vector-db-service"
    service_version: str = "1.0.0"
    
    # Collections
    blog_collection: str = "raw_blog_content"
    question_collection: str = "processed_questions"
    summary_collection: str = "blog_summaries"


# Global settings instance
settings = Settings()

