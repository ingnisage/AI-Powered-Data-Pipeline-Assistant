# backend/services/exceptions.py - Custom Exception Classes
"""
Custom exception classes for ai_workbench components to provide more structured error handling.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AiWorkbenchError(Exception):
    """Base exception class for all ai_workbench related errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize base exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details for debugging
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        
        # Log the error when it's created
        logger.error(f"AiWorkbenchError: {message} (code: {error_code})")


class ConfigurationError(AiWorkbenchError):
    """Raised when there's a configuration issue."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIG_ERROR", details)


class ServiceInitializationError(AiWorkbenchError):
    """Raised when a service fails to initialize."""
    
    def __init__(self, service_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Failed to initialize {service_name}: {reason}"
        super().__init__(message, "SERVICE_INIT_ERROR", details)
        self.service_name = service_name
        self.reason = reason


class ProcessingError(AiWorkbenchError):
    """Raised when processing fails."""
    
    def __init__(self, operation: str, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Failed to process {operation}: {reason}"
        super().__init__(message, "PROCESSING_ERROR", details)
        self.operation = operation
        self.reason = reason


class NetworkError(AiWorkbenchError):
    """Raised when there's a network connectivity issue."""
    
    def __init__(self, service: str, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Network error with {service}: {reason}"
        super().__init__(message, "NETWORK_ERROR", details)
        self.service = service
        self.reason = reason


class AuthenticationError(AiWorkbenchError):
    """Raised when authentication fails."""
    
    def __init__(self, service: str, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Authentication failed for {service}: {reason}"
        super().__init__(message, "AUTH_ERROR", details)
        self.service = service
        self.reason = reason


class RateLimitError(AiWorkbenchError):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, service: str, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        message = f"Rate limit exceeded for {service}"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        super().__init__(message, "RATE_LIMIT_ERROR", details)
        self.service = service
        self.retry_after = retry_after


class ValidationError(AiWorkbenchError):
    """Raised when input validation fails."""
    
    def __init__(self, field: str, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Validation failed for {field}: {reason}"
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.reason = reason


def handle_exception(e: Exception, context: str = "", component: str = "unknown") -> Dict[str, Any]:
    """Handle exceptions in a standardized way.
    
    Args:
        e: The exception that occurred
        context: Context where the error occurred
        component: Component where the error occurred
        
    Returns:
        Dictionary with error information for API responses
    """
    logger.error(f"Exception in {component} [{context}]: {str(e)}", exc_info=True)
    
    # Handle our custom exceptions
    if isinstance(e, AiWorkbenchError):
        return {
            "success": False,
            "error": {
                "type": e.__class__.__name__,
                "message": e.message,
                "code": e.error_code,
                "details": e.details,
                "context": context,
                "component": component
            }
        }
    
    # Handle common Python exceptions
    elif isinstance(e, ValueError):
        return {
            "success": False,
            "error": {
                "type": "ValueError",
                "message": str(e),
                "code": "VALUE_ERROR",
                "details": {"exception_type": type(e).__name__},
                "context": context,
                "component": component
            }
        }
    elif isinstance(e, TypeError):
        return {
            "success": False,
            "error": {
                "type": "TypeError",
                "message": str(e),
                "code": "TYPE_ERROR",
                "details": {"exception_type": type(e).__name__},
                "context": context,
                "component": component
            }
        }
    elif isinstance(e, KeyError):
        return {
            "success": False,
            "error": {
                "type": "KeyError",
                "message": str(e),
                "code": "KEY_ERROR",
                "details": {"exception_type": type(e).__name__},
                "context": context,
                "component": component
            }
        }
    
    # Handle all other exceptions
    else:
        return {
            "success": False,
            "error": {
                "type": type(e).__name__,
                "message": str(e),
                "code": "UNKNOWN_ERROR",
                "details": {"exception_type": type(e).__name__},
                "context": context,
                "component": component
            }
        }


def safe_execute(func, *args, **kwargs):
    """Safely execute a function and handle any exceptions.
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function or error dictionary
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return handle_exception(e, context=func.__name__)