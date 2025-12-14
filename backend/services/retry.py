# backend/services/retry.py - Retry Mechanisms
"""
Retry mechanisms with exponential backoff for ai_workbench components.
"""

import asyncio
import logging
import random
import time
from typing import Callable, Any, Optional, Type, Tuple, Union
from functools import wraps

from .exceptions import NetworkError, RateLimitError

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry mechanisms."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on_exceptions: Tuple[Type[Exception], ...] = (
            NetworkError, 
            RateLimitError,
            ConnectionError,
            TimeoutError
        )
    ):
        """Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
            retry_on_exceptions: Tuple of exception types to retry on
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on_exceptions = retry_on_exceptions


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay with exponential backoff and optional jitter.
    
    Args:
        attempt: Current attempt number (1-indexed)
        config: Retry configuration
        
    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * (exponential_base ^ (attempt - 1))
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))
    
    # Cap at max_delay
    delay = min(delay, config.max_delay)
    
    # Add jitter if enabled
    if config.jitter:
        delay = delay * (0.5 + random.random() * 0.5)  # 0.5 to 1.0 multiplier
    
    return delay


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """Decorator for retrying functions with exponential backoff.
    
    Args:
        config: Retry configuration (uses default if None)
        
    Returns:
        Decorator function
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retry_on_exceptions as e:
                    last_exception = e
                    
                    # If this is the last attempt, re-raise
                    if attempt == config.max_attempts:
                        logger.error(f"Function {func.__name__} failed after {config.max_attempts} attempts: {e}")
                        raise
                    
                    # Calculate and apply delay
                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt} of {func.__name__} failed: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    # Handle rate limit errors specially
                    if isinstance(e, RateLimitError) and e.retry_after:
                        delay = max(delay, e.retry_after)
                    
                    await asyncio.sleep(delay)
            
            # This should never be reached due to the re-raise above
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.retry_on_exceptions as e:
                    last_exception = e
                    
                    # If this is the last attempt, re-raise
                    if attempt == config.max_attempts:
                        logger.error(f"Function {func.__name__} failed after {config.max_attempts} attempts: {e}")
                        raise
                    
                    # Calculate and apply delay
                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt} of {func.__name__} failed: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    # Handle rate limit errors specially
                    if isinstance(e, RateLimitError) and e.retry_after:
                        delay = max(delay, e.retry_after)
                    
                    time.sleep(delay)
            
            # This should never be reached due to the re-raise above
            raise last_exception
        
        # Return appropriate wrapper based on whether function is async
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Predefined retry configurations for common scenarios
DEFAULT_RETRY_CONFIG = RetryConfig()

NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=2.0,
    max_delay=120.0,
    exponential_base=2.0,
    retry_on_exceptions=(
        NetworkError,
        ConnectionError,
        TimeoutError
    )
)

API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    retry_on_exceptions=(
        NetworkError,
        RateLimitError,
        ConnectionError,
        TimeoutError
    )
)


def retry_sync_operation(
    operation: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """Retry a synchronous operation with exponential backoff.
    
    Args:
        operation: Function to retry
        *args: Positional arguments for the operation
        config: Retry configuration
        **kwargs: Keyword arguments for the operation
        
    Returns:
        Result of the operation
        
    Raises:
        Exception: Last exception if all retries fail
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            return operation(*args, **kwargs)
        except config.retry_on_exceptions as e:
            last_exception = e
            
            # If this is the last attempt, re-raise
            if attempt == config.max_attempts:
                logger.error(f"Operation {operation.__name__} failed after {config.max_attempts} attempts: {e}")
                raise
            
            # Calculate and apply delay
            delay = calculate_delay(attempt, config)
            logger.warning(
                f"Attempt {attempt} of {operation.__name__} failed: {e}. "
                f"Retrying in {delay:.2f} seconds..."
            )
            
            # Handle rate limit errors specially
            if isinstance(e, RateLimitError) and e.retry_after:
                delay = max(delay, e.retry_after)
            
            time.sleep(delay)
    
    # This should never be reached due to the re-raise above
    raise last_exception


async def retry_async_operation(
    operation: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """Retry an asynchronous operation with exponential backoff.
    
    Args:
        operation: Async function to retry
        *args: Positional arguments for the operation
        config: Retry configuration
        **kwargs: Keyword arguments for the operation
        
    Returns:
        Result of the operation
        
    Raises:
        Exception: Last exception if all retries fail
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            return await operation(*args, **kwargs)
        except config.retry_on_exceptions as e:
            last_exception = e
            
            # If this is the last attempt, re-raise
            if attempt == config.max_attempts:
                logger.error(f"Async operation {operation.__name__} failed after {config.max_attempts} attempts: {e}")
                raise
            
            # Calculate and apply delay
            delay = calculate_delay(attempt, config)
            logger.warning(
                f"Attempt {attempt} of {operation.__name__} failed: {e}. "
                f"Retrying in {delay:.2f} seconds..."
            )
            
            # Handle rate limit errors specially
            if isinstance(e, RateLimitError) and e.retry_after:
                delay = max(delay, e.retry_after)
            
            await asyncio.sleep(delay)
    
    # This should never be reached due to the re-raise above
    raise last_exception