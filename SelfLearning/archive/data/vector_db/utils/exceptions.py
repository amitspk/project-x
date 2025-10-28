"""
Custom exceptions for the vector database module.

This module defines a hierarchy of exceptions that provide detailed
error information for different failure scenarios in the vector database system.
"""

from typing import Optional, Dict, Any


class VectorDBError(Exception):
    """
    Base exception for all vector database errors.
    
    Provides a consistent interface for error handling across
    the entire vector database system.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize vector database error.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'cause': str(self.cause) if self.cause else None
        }
    
    def __str__(self) -> str:
        """String representation of the error."""
        base_msg = f"{self.error_code}: {self.message}"
        
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base_msg += f" ({details_str})"
        
        if self.cause:
            base_msg += f" [Caused by: {self.cause}]"
        
        return base_msg


class EmbeddingError(VectorDBError):
    """
    Exception raised when embedding generation fails.
    
    This includes failures in:
    - API communication with embedding providers
    - Invalid input text or parameters
    - Model-specific errors
    - Rate limiting or quota issues
    """
    
    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        input_text_length: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize embedding error.
        
        Args:
            message: Error message
            provider: Embedding provider name
            model: Embedding model name
            input_text_length: Length of input text that failed
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get('details', {})
        if provider:
            details['provider'] = provider
        if model:
            details['model'] = model
        if input_text_length:
            details['input_text_length'] = input_text_length
        
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class VectorStoreError(VectorDBError):
    """
    Exception raised when vector store operations fail.
    
    This includes failures in:
    - Database connection and initialization
    - Document CRUD operations
    - Index management
    - Storage backend specific errors
    """
    
    def __init__(
        self,
        message: str,
        store_type: Optional[str] = None,
        operation: Optional[str] = None,
        document_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize vector store error.
        
        Args:
            message: Error message
            store_type: Type of vector store (e.g., 'chroma', 'faiss')
            operation: Operation that failed (e.g., 'add', 'search', 'delete')
            document_id: ID of document involved in the operation
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get('details', {})
        if store_type:
            details['store_type'] = store_type
        if operation:
            details['operation'] = operation
        if document_id:
            details['document_id'] = document_id
        
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class VectorSearchError(VectorDBError):
    """
    Exception raised when vector search operations fail.
    
    This includes failures in:
    - Query processing and embedding generation
    - Similarity search execution
    - Result filtering and ranking
    - Search service coordination
    """
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        search_type: Optional[str] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize vector search error.
        
        Args:
            message: Error message
            query: Search query that failed
            search_type: Type of search operation
            filter_criteria: Filter criteria used in search
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get('details', {})
        if query:
            details['query'] = query[:100] + "..." if len(query) > 100 else query
        if search_type:
            details['search_type'] = search_type
        if filter_criteria:
            details['filter_criteria'] = filter_criteria
        
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class ConfigurationError(VectorDBError):
    """
    Exception raised when configuration is invalid or missing.
    
    This includes failures in:
    - Missing required configuration parameters
    - Invalid configuration values
    - Environment setup issues
    - Provider authentication problems
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[str] = None,
        required_keys: Optional[list] = None,
        **kwargs
    ):
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            config_key: Configuration key that caused the error
            config_value: Invalid configuration value
            required_keys: List of required configuration keys
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get('details', {})
        if config_key:
            details['config_key'] = config_key
        if config_value:
            details['config_value'] = config_value
        if required_keys:
            details['required_keys'] = required_keys
        
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class ValidationError(VectorDBError):
    """
    Exception raised when input validation fails.
    
    This includes failures in:
    - Invalid input parameters
    - Data format validation
    - Business rule violations
    - Constraint violations
    """
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field_name: Name of field that failed validation
            field_value: Value that failed validation
            validation_rule: Validation rule that was violated
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get('details', {})
        if field_name:
            details['field_name'] = field_name
        if field_value is not None:
            details['field_value'] = str(field_value)
        if validation_rule:
            details['validation_rule'] = validation_rule
        
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class ResourceNotFoundError(VectorDBError):
    """
    Exception raised when a requested resource is not found.
    
    This includes:
    - Document not found by ID
    - Collection or index not found
    - Configuration file not found
    - Model or provider not available
    """
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize resource not found error.
        
        Args:
            message: Error message
            resource_type: Type of resource (e.g., 'document', 'collection')
            resource_id: ID of the resource that was not found
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get('details', {})
        if resource_type:
            details['resource_type'] = resource_type
        if resource_id:
            details['resource_id'] = resource_id
        
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class RateLimitError(VectorDBError):
    """
    Exception raised when rate limits are exceeded.
    
    This includes:
    - API rate limits from embedding providers
    - Database connection limits
    - Request throttling
    - Quota exhaustion
    """
    
    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        retry_after: Optional[int] = None,
        current_usage: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize rate limit error.
        
        Args:
            message: Error message
            provider: Provider that imposed the rate limit
            retry_after: Seconds to wait before retrying
            current_usage: Current usage count
            limit: Rate limit threshold
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get('details', {})
        if provider:
            details['provider'] = provider
        if retry_after:
            details['retry_after'] = retry_after
        if current_usage:
            details['current_usage'] = current_usage
        if limit:
            details['limit'] = limit
        
        kwargs['details'] = details
        super().__init__(message, **kwargs)
