"""
Configuration management for the web crawler system.

Provides centralized configuration with environment variable support,
validation, and production-ready defaults.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set
from pathlib import Path
from ..utils.exceptions import ConfigurationError


@dataclass
class CrawlerConfig:
    """Configuration settings for the web crawler."""
    
    # Network settings
    timeout: int = 30
    max_retries: int = 3
    delay_between_requests: float = 1.0
    max_concurrent_requests: int = 5
    
    # User agent settings
    user_agent: str = "WebCrawler/1.0 (Production)"
    
    # Content settings
    max_content_size: int = 10 * 1024 * 1024  # 10MB
    allowed_content_types: Set[str] = field(default_factory=lambda: {
        'text/html', 'text/plain', 'application/xhtml+xml'
    })
    
    # Storage settings
    output_directory: Path = field(default_factory=lambda: Path("./crawled_content"))
    max_filename_length: int = 100
    create_subdirectories: bool = True
    
    # Security settings
    allow_local_urls: bool = False
    follow_redirects: bool = True
    max_redirects: int = 5
    verify_ssl: bool = True
    
    # Rate limiting
    requests_per_minute: int = 60
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[Path] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()
        self._setup_directories()
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        if self.timeout <= 0:
            raise ConfigurationError("Timeout must be positive")
        
        if self.max_retries < 0:
            raise ConfigurationError("Max retries cannot be negative")
        
        if self.delay_between_requests < 0:
            raise ConfigurationError("Delay between requests cannot be negative")
        
        if self.max_concurrent_requests <= 0:
            raise ConfigurationError("Max concurrent requests must be positive")
        
        if self.max_content_size <= 0:
            raise ConfigurationError("Max content size must be positive")
        
        if not self.user_agent.strip():
            raise ConfigurationError("User agent cannot be empty")
        
        if self.requests_per_minute <= 0:
            raise ConfigurationError("Requests per minute must be positive")
        
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigurationError(f"Invalid log level: {self.log_level}")
    
    def _setup_directories(self) -> None:
        """Create necessary directories."""
        try:
            self.output_directory.mkdir(parents=True, exist_ok=True)
            
            if self.log_file:
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            raise ConfigurationError(f"Failed to create directories: {e}")
    
    @classmethod
    def from_env(cls, prefix: str = "CRAWLER_") -> "CrawlerConfig":
        """
        Create configuration from environment variables.
        
        Args:
            prefix: Environment variable prefix
            
        Returns:
            CrawlerConfig instance
        """
        config_dict = {}
        
        # Map environment variables to config fields
        env_mappings = {
            f"{prefix}TIMEOUT": ("timeout", int),
            f"{prefix}MAX_RETRIES": ("max_retries", int),
            f"{prefix}DELAY": ("delay_between_requests", float),
            f"{prefix}MAX_CONCURRENT": ("max_concurrent_requests", int),
            f"{prefix}USER_AGENT": ("user_agent", str),
            f"{prefix}MAX_CONTENT_SIZE": ("max_content_size", int),
            f"{prefix}OUTPUT_DIR": ("output_directory", Path),
            f"{prefix}ALLOW_LOCAL": ("allow_local_urls", cls._str_to_bool),
            f"{prefix}FOLLOW_REDIRECTS": ("follow_redirects", cls._str_to_bool),
            f"{prefix}MAX_REDIRECTS": ("max_redirects", int),
            f"{prefix}VERIFY_SSL": ("verify_ssl", cls._str_to_bool),
            f"{prefix}REQUESTS_PER_MINUTE": ("requests_per_minute", int),
            f"{prefix}LOG_LEVEL": ("log_level", str),
            f"{prefix}LOG_FORMAT": ("log_format", str),
            f"{prefix}LOG_FILE": ("log_file", lambda x: Path(x) if x else None),
        }
        
        for env_var, (field_name, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    config_dict[field_name] = converter(value)
                except (ValueError, TypeError) as e:
                    raise ConfigurationError(f"Invalid value for {env_var}: {value} ({e})")
        
        return cls(**config_dict)
    
    @staticmethod
    def _str_to_bool(value: str) -> bool:
        """Convert string to boolean."""
        return value.lower() in ("true", "1", "yes", "on")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                result[key] = str(value)
            elif isinstance(value, set):
                result[key] = list(value)
            else:
                result[key] = value
        return result
    
    def update(self, **kwargs) -> "CrawlerConfig":
        """
        Create a new configuration with updated values.
        
        Args:
            **kwargs: Configuration values to update
            
        Returns:
            New CrawlerConfig instance
        """
        current_dict = self.to_dict()
        current_dict.update(kwargs)
        
        # Convert back special types
        if 'output_directory' in current_dict:
            current_dict['output_directory'] = Path(current_dict['output_directory'])
        if 'log_file' in current_dict and current_dict['log_file']:
            current_dict['log_file'] = Path(current_dict['log_file'])
        if 'allowed_content_types' in current_dict:
            current_dict['allowed_content_types'] = set(current_dict['allowed_content_types'])
        
        return CrawlerConfig(**current_dict)
