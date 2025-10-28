"""
MongoDB configuration settings.

This module contains configuration settings for MongoDB connection
and database operations.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class MongoDBSettings:
    """MongoDB connection and configuration settings."""
    
    # Connection settings
    host: str = "localhost"
    port: int = 27017
    username: str = "admin"
    password: str = "password123"
    database: str = "blog_ai_db"
    auth_source: str = "admin"
    
    # Connection options
    max_pool_size: int = 100
    min_pool_size: int = 0
    max_idle_time_ms: int = 30000
    server_selection_timeout_ms: int = 5000
    connect_timeout_ms: int = 10000
    socket_timeout_ms: int = 20000
    
    # SSL settings
    use_ssl: bool = False
    ssl_cert_file: Optional[str] = None
    ssl_key_file: Optional[str] = None
    ssl_ca_file: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'MongoDBSettings':
        """Create settings from environment variables."""
        return cls(
            host=os.getenv('MONGODB_HOST', 'localhost'),
            port=int(os.getenv('MONGODB_PORT', '27017')),
            username=os.getenv('MONGODB_USERNAME', 'admin'),
            password=os.getenv('MONGODB_PASSWORD', 'password123'),
            database=os.getenv('MONGODB_DATABASE', 'blog_ai_db'),
            auth_source=os.getenv('MONGODB_AUTH_SOURCE', 'admin'),
            max_pool_size=int(os.getenv('MONGODB_MAX_POOL_SIZE', '100')),
            min_pool_size=int(os.getenv('MONGODB_MIN_POOL_SIZE', '0')),
            use_ssl=os.getenv('MONGODB_USE_SSL', 'false').lower() == 'true',
            ssl_cert_file=os.getenv('MONGODB_SSL_CERT_FILE'),
            ssl_key_file=os.getenv('MONGODB_SSL_KEY_FILE'),
            ssl_ca_file=os.getenv('MONGODB_SSL_CA_FILE')
        )
    
    def get_connection_string(self) -> str:
        """Generate MongoDB connection string."""
        if self.username and self.password:
            auth_part = f"{self.username}:{self.password}@"
        else:
            auth_part = ""
        
        base_url = f"mongodb://{auth_part}{self.host}:{self.port}/{self.database}"
        
        # Add connection options
        options = []
        if self.auth_source and self.username:
            options.append(f"authSource={self.auth_source}")
        if self.max_pool_size:
            options.append(f"maxPoolSize={self.max_pool_size}")
        if self.min_pool_size:
            options.append(f"minPoolSize={self.min_pool_size}")
        if self.server_selection_timeout_ms:
            options.append(f"serverSelectionTimeoutMS={self.server_selection_timeout_ms}")
        if self.connect_timeout_ms:
            options.append(f"connectTimeoutMS={self.connect_timeout_ms}")
        if self.socket_timeout_ms:
            options.append(f"socketTimeoutMS={self.socket_timeout_ms}")
        if self.use_ssl:
            options.append("ssl=true")
        
        if options:
            base_url += "?" + "&".join(options)
        
        return base_url
    
    def get_connection_options(self) -> dict:
        """Get connection options as dictionary."""
        options = {
            'maxPoolSize': self.max_pool_size,
            'minPoolSize': self.min_pool_size,
            'maxIdleTimeMS': self.max_idle_time_ms,
            'serverSelectionTimeoutMS': self.server_selection_timeout_ms,
            'connectTimeoutMS': self.connect_timeout_ms,
            'socketTimeoutMS': self.socket_timeout_ms
        }
        
        if self.use_ssl:
            options['ssl'] = True
            if self.ssl_cert_file:
                options['ssl_certfile'] = self.ssl_cert_file
            if self.ssl_key_file:
                options['ssl_keyfile'] = self.ssl_key_file
            if self.ssl_ca_file:
                options['ssl_ca_certs'] = self.ssl_ca_file
        
        return options


# Default settings instance
DEFAULT_SETTINGS = MongoDBSettings()

# Environment-based settings instance
ENV_SETTINGS = MongoDBSettings.from_env()
