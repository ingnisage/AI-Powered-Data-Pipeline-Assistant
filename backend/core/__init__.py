# core/__init__.py
"""Core application modules for dependency injection and error handling."""

from .dependencies import (
    ServiceContainer,
    get_container,
    lifespan,
    get_openai_client,
    get_supabase_client,
    get_pubnub_client,
    get_search_service,
    get_vector_service,
    get_service_health,
)

from .errors import (
    ErrorCode,
    ErrorResponse,
    AppError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    RateLimitError,
    ServiceError,
    DatabaseError,
    ToolExecutionError,
    app_error_handler,
    generic_exception_handler,
    safe_execute,
)

__all__ = [
    # Dependencies
    'ServiceContainer',
    'get_container',
    'lifespan',
    'get_openai_client',
    'get_supabase_client',
    'get_pubnub_client',
    'get_search_service',
    'get_vector_service',
    'get_service_health',
    
    # Errors
    'ErrorCode',
    'ErrorResponse',
    'AppError',
    'ValidationError',
    'AuthenticationError',
    'AuthorizationError',
    'ResourceNotFoundError',
    'RateLimitError',
    'ServiceError',
    'DatabaseError',
    'ToolExecutionError',
    'app_error_handler',
    'generic_exception_handler',
    'safe_execute',
]