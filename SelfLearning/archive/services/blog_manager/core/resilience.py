"""
Resilience patterns for production-grade microservices.

Implements:
- Circuit Breaker pattern for fault tolerance
- Retry mechanisms with exponential backoff
- Timeout handling
- Fallback strategies
"""

import logging
import asyncio
from typing import Optional, Callable, Any, TypeVar, Dict
from functools import wraps
from datetime import datetime, timedelta

from pybreaker import CircuitBreaker, CircuitBreakerError, CircuitBreakerState

logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')


class ServiceCircuitBreakers:
    """
    Centralized circuit breaker management for all external dependencies.
    
    Circuit breaker states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered, allow one request
    """
    
    def __init__(self):
        """Initialize circuit breakers for all external services."""
        
        # LLM Service Circuit Breaker
        self.llm_service = CircuitBreaker(
            fail_max=5,  # Open circuit after 5 consecutive failures
            reset_timeout=60,  # Stay open for 60 seconds
            name="llm_service",
            listeners=circuit_breaker_listeners()
        )
        
        # MongoDB Circuit Breaker
        self.mongodb = CircuitBreaker(
            fail_max=3,  # Open after 3 failures (database should be reliable)
            reset_timeout=30,  # Shorter timeout for database
            name="mongodb",
            listeners=circuit_breaker_listeners()
        )
        
        # Vector DB Circuit Breaker
        self.vector_db = CircuitBreaker(
            fail_max=5,
            reset_timeout=60,
            name="vector_db",
            listeners=circuit_breaker_listeners()
        )
        
        # Web Crawler Circuit Breaker
        self.crawler = CircuitBreaker(
            fail_max=5,
            reset_timeout=90,  # Longer timeout for external websites
            name="crawler",
            listeners=circuit_breaker_listeners()
        )
        
        # External API Circuit Breaker (for third-party APIs)
        self.external_api = CircuitBreaker(
            fail_max=5,
            reset_timeout=120,
            name="external_api",
            listeners=circuit_breaker_listeners()
        )
    
    def get_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers for health monitoring."""
        breakers = {
            "llm_service": self.llm_service,
            "mongodb": self.mongodb,
            "vector_db": self.vector_db,
            "crawler": self.crawler,
            "external_api": self.external_api
        }
        
        status = {}
        for name, breaker in breakers.items():
            state_name = breaker.current_state
            status[name] = {
                "state": state_name,
                "failure_count": breaker.fail_counter,
                "success_count": breaker.success_counter,
                "fail_max": breaker.fail_max,
                "reset_timeout": breaker.reset_timeout,
                "name": breaker.name or name
            }
        
        return status
    
    def reset_all(self):
        """Reset all circuit breakers (useful for testing or manual recovery)."""
        breakers = [
            self.llm_service,
            self.mongodb,
            self.vector_db,
            self.crawler,
            self.external_api
        ]
        
        for breaker in breakers:
            try:
                breaker.close()
                logger.info(f"Reset circuit breaker: {breaker.name}")
            except Exception as e:
                logger.error(f"Failed to reset breaker {breaker.name}: {e}")


def circuit_breaker_listeners():
    """Create circuit breaker event listeners for logging and monitoring."""
    
    class CircuitBreakerListener:
        """Listener for circuit breaker state changes."""
        
        def state_change(self, breaker: CircuitBreaker, old_state: CircuitBreakerState, new_state: CircuitBreakerState):
            """Called when circuit breaker changes state."""
            logger.warning(
                f"Circuit breaker '{breaker.name}' state changed: {old_state} → {new_state}. "
                f"Failure count: {breaker.fail_counter}"
            )
        
        def failure(self, breaker: CircuitBreaker, exc: Exception):
            """Called when a failure occurs."""
            logger.error(
                f"Circuit breaker '{breaker.name}' recorded failure ({breaker.fail_counter}/{breaker.fail_max}): {exc}"
            )
        
        def success(self, breaker: CircuitBreaker):
            """Called when a successful call occurs."""
            logger.debug(f"Circuit breaker '{breaker.name}' recorded success")
        
        def before_call(self, breaker: CircuitBreaker, func: Callable, *args, **kwargs):
            """Called before executing the protected function."""
            logger.debug(f"Circuit breaker '{breaker.name}' executing call")
    
    return [CircuitBreakerListener()]


# Global circuit breaker instance
_circuit_breakers: Optional[ServiceCircuitBreakers] = None


def get_circuit_breakers() -> ServiceCircuitBreakers:
    """Get the global circuit breaker instance (singleton)."""
    global _circuit_breakers
    if _circuit_breakers is None:
        _circuit_breakers = ServiceCircuitBreakers()
        logger.info("Initialized circuit breakers for all services")
    return _circuit_breakers


def with_circuit_breaker(breaker_name: str, fallback: Optional[Callable] = None):
    """
    Decorator to protect async functions with a circuit breaker.
    
    Args:
        breaker_name: Name of the circuit breaker to use ('llm_service', 'mongodb', etc.)
        fallback: Optional fallback function to call if circuit is open
    
    Example:
        @with_circuit_breaker('llm_service', fallback=lambda *args, **kwargs: "Service unavailable")
        async def call_llm_service(prompt: str):
            return await llm.generate(prompt)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            breakers = get_circuit_breakers()
            breaker = getattr(breakers, breaker_name, None)
            
            if breaker is None:
                logger.error(f"Unknown circuit breaker: {breaker_name}")
                return await func(*args, **kwargs)
            
            try:
                # Execute function with circuit breaker protection
                # Note: pybreaker doesn't natively support async, so we wrap it
                result = await asyncio.to_thread(
                    breaker.call,
                    lambda: asyncio.run(func(*args, **kwargs))
                )
                return result
                
            except CircuitBreakerError as e:
                # Circuit is open, service is unavailable
                logger.warning(
                    f"Circuit breaker '{breaker_name}' is OPEN. "
                    f"Service unavailable. Using fallback if available."
                )
                
                if fallback:
                    return fallback(*args, **kwargs)
                
                # Re-raise as a more informative exception
                raise ServiceUnavailableError(
                    f"Service '{breaker_name}' is temporarily unavailable due to repeated failures. "
                    f"Circuit breaker is OPEN. Please try again later.",
                    service_name=breaker_name,
                    breaker_state=str(breaker.state)
                ) from e
            
            except Exception as e:
                # Unexpected error, let it propagate
                logger.error(f"Error in circuit breaker '{breaker_name}': {e}")
                raise
        
        return wrapper
    return decorator


def with_circuit_breaker_sync(breaker_name: str, fallback: Optional[Callable] = None):
    """
    Decorator to protect synchronous functions with a circuit breaker.
    
    Args:
        breaker_name: Name of the circuit breaker to use
        fallback: Optional fallback function to call if circuit is open
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            breakers = get_circuit_breakers()
            breaker = getattr(breakers, breaker_name, None)
            
            if breaker is None:
                logger.error(f"Unknown circuit breaker: {breaker_name}")
                return func(*args, **kwargs)
            
            try:
                return breaker.call(func, *args, **kwargs)
                
            except CircuitBreakerError as e:
                logger.warning(f"Circuit breaker '{breaker_name}' is OPEN. Using fallback if available.")
                
                if fallback:
                    return fallback(*args, **kwargs)
                
                raise ServiceUnavailableError(
                    f"Service '{breaker_name}' is temporarily unavailable.",
                    service_name=breaker_name,
                    breaker_state=str(breaker.state)
                ) from e
        
        return wrapper
    return decorator


class ServiceUnavailableError(Exception):
    """
    Raised when a service is unavailable due to an open circuit breaker.
    
    This is a more user-friendly exception than CircuitBreakerError.
    """
    
    def __init__(self, message: str, service_name: str, breaker_state: str):
        super().__init__(message)
        self.service_name = service_name
        self.breaker_state = breaker_state
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": "service_unavailable",
            "message": str(self),
            "service": self.service_name,
            "breaker_state": self.breaker_state,
            "timestamp": self.timestamp.isoformat(),
            "retry_after": "Please try again in a few moments"
        }


async def with_timeout(coro, timeout_seconds: float = 30.0):
    """
    Execute an async function with a timeout.
    
    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds
    
    Raises:
        asyncio.TimeoutError: If operation exceeds timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.error(f"Operation timed out after {timeout_seconds} seconds")
        raise


async def with_retry(
    coro_func: Callable,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,)
):
    """
    Execute an async function with exponential backoff retry.
    
    Args:
        coro_func: Async function to call
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each failure
        max_delay: Maximum delay between retries
        exceptions: Tuple of exceptions to catch and retry
    
    Returns:
        Result of the function call
    
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_func()
        except exceptions as e:
            last_exception = e
            
            if attempt == max_attempts:
                logger.error(f"All {max_attempts} retry attempts failed. Last error: {e}")
                raise
            
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed: {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            
            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)
    
    # Should never reach here, but just in case
    raise last_exception if last_exception else Exception("Retry failed")

