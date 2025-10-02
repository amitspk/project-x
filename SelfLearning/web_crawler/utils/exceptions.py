"""
Custom exception hierarchy for the web crawler system.

Provides specific exception types for different error scenarios
to enable proper error handling and debugging.
"""


class CrawlerError(Exception):
    """Base exception for all crawler-related errors."""
    
    def __init__(self, message: str, url: str = None, status_code: int = None):
        self.message = message
        self.url = url
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(CrawlerError):
    """Raised when input validation fails."""
    pass


class NetworkError(CrawlerError):
    """Raised when network-related errors occur."""
    pass


class ContentExtractionError(CrawlerError):
    """Raised when content extraction fails."""
    pass


class StorageError(CrawlerError):
    """Raised when storage operations fail."""
    
    def __init__(self, message: str, file_path: str = None):
        self.file_path = file_path
        super().__init__(message)


class ConfigurationError(CrawlerError):
    """Raised when configuration is invalid."""
    pass


class RateLimitError(CrawlerError):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(message)
