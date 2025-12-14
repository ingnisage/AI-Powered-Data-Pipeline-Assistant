# core/errors.py - Standardized Error Handling
"""
Centralized error handling with consistent patterns and structured logging.
Replaces mixed error handling patterns with a unified approach.
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standardized error codes for the application."""
    
    # Client errors (4xx)
    INVALID_INPUT = "INVALID_INPUT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    
    # Business logic errors
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    AI_MODEL_ERROR = "AI_MODEL_ERROR"
    DATA_PROCESSING_ERROR = "DATA_PROCESSING_ERROR"


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error_code: str
    message: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: Optional[str] = None


class AppError(Exception):
    """Base exception for all application errors.
    
    Provides structured error handling with logging and HTTP status mapping.
    """
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[str] = None,
        log_level: int = logging.ERROR,
        **context
    ):
        """Initialize application error.
        
        Args:
            message: User-facing error message
            error_code: Standardized error code
            status_code: HTTP status code
            detail: Additional error details (for debugging)
            log_level: Logging level for this error
            **context: Additional context for logging
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.detail = detail
        self.log_level = log_level
        self.context = context
        
        super().__init__(message)
        
        # Log the error
        self._log_error()
    
    def _log_error(self) -> None:
        """Log the error with appropriate level and context."""
        log_data = {
            "error_code": self.error_code.value,
            "message": self.message,
            "status_code": self.status_code,
            **self.context
        }
        
        if self.detail:
            log_data["detail"] = self.detail
        
        # Log with sanitization (if integrated)
        logger.log(
            self.log_level,
            f"{self.error_code.value}: {self.message}",
            extra=log_data
        )
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException.
        
        Returns:
            HTTPException with appropriate status code and detail
        """
        return HTTPException(
            status_code=self.status_code,
            detail={
                "error_code": self.error_code.value,
                "message": self.message,
                "detail": self.detail
            }
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON response.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "detail": self.detail
        }


# Specific error classes for common scenarios
class ValidationError(AppError):
    """Error for invalid input data."""
    
    def __init__(self, message: str, detail: Optional[str] = None, **context):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            log_level=logging.WARNING,
            **context
        )


class AuthenticationError(AppError):
    """Error for authentication failures."""
    
    def __init__(self, message: str = "Authentication failed", detail: Optional[str] = None, **context):
        super().__init__(
            message=message,
            error_code=ErrorCode.UNAUTHORIZED,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            log_level=logging.WARNING,
            **context
        )


class AuthorizationError(AppError):
    """Error for authorization failures."""
    
    def __init__(self, message: str = "Access denied", detail: Optional[str] = None, **context):
        super().__init__(
            message=message,
            error_code=ErrorCode.FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            log_level=logging.WARNING,
            **context
        )


class ResourceNotFoundError(AppError):
    """Error for resource not found."""
    
    def __init__(self, resource: str, identifier: Optional[str] = None, **context):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=None,
            log_level=logging.INFO,
            **context
        )


class RateLimitError(AppError):
    """Error for rate limit exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60, **context):
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Retry after {retry_after} seconds",
            log_level=logging.WARNING,
            retry_after=retry_after,
            **context
        )


class ServiceError(AppError):
    """Error for external service failures."""
    
    def __init__(self, service: str, message: str, detail: Optional[str] = None, **context):
        super().__init__(
            message=f"{service} service error: {message}",
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            log_level=logging.ERROR,
            service=service,
            **context
        )


class DatabaseError(AppError):
    """Error for database operations."""
    
    def __init__(self, message: str, detail: Optional[str] = None, **context):
        super().__init__(
            message=f"Database error: {message}",
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            log_level=logging.ERROR,
            **context
        )


class ToolExecutionError(AppError):
    """Error for AI tool execution failures."""
    
    def __init__(self, tool_name: str, message: str, detail: Optional[str] = None, **context):
        super().__init__(
            message=f"Tool '{tool_name}' execution failed: {message}",
            error_code=ErrorCode.TOOL_EXECUTION_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            log_level=logging.ERROR,
            tool_name=tool_name,
            **context
        )


# Global exception handler for FastAPI
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Global exception handler for AppError and subclasses.
    
    Args:
        request: FastAPI request
        exc: Application error
        
    Returns:
        JSON response with error details
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unexpected exceptions.
    
    Args:
        request: FastAPI request
        exc: Unexpected exception
        
    Returns:
        JSON response with generic error message
    """
    # Log the unexpected error with full traceback
    logger.error(
        f"Unexpected error: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={"path": request.url.path, "method": request.method}
    )
    
    # Return generic error to user (don't expose internals)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": ErrorCode.INTERNAL_ERROR.value,
            "message": "An unexpected error occurred",
            "detail": None  # Never expose internal error details to users
        }
    )


# Helper function for safe error handling in tools
def safe_execute(func, *args, error_message: str = "Operation failed", **kwargs):
    """Execute a function with standardized error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments for func
        error_message: Error message if execution fails
        **kwargs: Keyword arguments for func
        
    Returns:
        Result of func execution
        
    Raises:
        AppError: If execution fails
    """
    try:
        return func(*args, **kwargs)
    except AppError:
        # Re-raise application errors as-is
        raise
    except Exception as e:
        # Wrap unexpected errors
        logger.error(f"{error_message}: {type(e).__name__}: {str(e)}", exc_info=True)
        raise AppError(
            message=error_message,
            error_code=ErrorCode.INTERNAL_ERROR,
            detail=str(e)
        ) from e
