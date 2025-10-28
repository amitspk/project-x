"""
Configuration for Content Processing Service.

Consolidated service combining crawler, database, and LLM operations.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Service configuration."""
    
    # Service
    service_name: str = "content-processing-service"
    service_version: str = "1.0.0"
    port: int = int(os.getenv("PORT", "8005"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # MongoDB
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "blog_qa_db")
    mongodb_max_pool_size: int = int(os.getenv("MONGODB_MAX_POOL_SIZE", "100"))
    mongodb_min_pool_size: int = int(os.getenv("MONGODB_MIN_POOL_SIZE", "10"))
    
    # LLM (OpenAI)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    embedding_model: str = "text-embedding-ada-002"
    
    # Crawler
    crawler_timeout: int = int(os.getenv("CRAWLER_TIMEOUT", "30"))
    crawler_max_retries: int = int(os.getenv("CRAWLER_MAX_RETRIES", "3"))
    crawler_user_agent: str = "ContentBot/1.0 (Production)"
    crawler_max_content_size: int = 10 * 1024 * 1024  # 10MB
    
    # Processing
    async_processing: bool = True
    max_parallel_llm_calls: int = 3
    default_num_questions: int = 5
    
    # Collections
    blogs_collection: str = "raw_blog_content"
    questions_collection: str = "processed_questions"
    summaries_collection: str = "blog_summaries"
    
    # Performance
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour


# Global settings instance
settings = Settings()

