# backend/core/middleware.py - Core Middleware
"""
Core middleware for authentication, logging, and CORS.
"""

import logging
import time
from typing import Callable, Awaitable
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

class LoggingMiddleware:
    """Middleware for request/response logging."""
    
    def __init__(self, app):
        """Initialize middleware.
        
        Args:
            app: FastAPI application
        """
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """Process middleware.
        
        Args:
            scope: ASGI scope
            receive: Receive function
            send: Send function
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Create request object
        request = Request(scope, receive)
        
        # Log request
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        
        logger.info(f"Request: {method} {path} from {client_ip}")
        
        # Capture response
        async def send_with_logging(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration = (time.time() - start_time) * 1000  # ms
                logger.info(f"Response: {status_code} for {method} {path} ({duration:.2f}ms)")
            await send(message)
        
        # Process request
        await self.app(scope, receive, send_with_logging)


class AuthMiddleware:
    """Middleware for authentication checks."""
    
    def __init__(self, app, exclude_paths=None):
        """Initialize middleware.
        
        Args:
            app: FastAPI application
            exclude_paths: List of paths to exclude from auth
        """
        self.app = app
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json"]
    
    async def __call__(self, scope, receive, send):
        """Process middleware.
        
        Args:
            scope: ASGI scope
            receive: Receive function
            send: Send function
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check if path should be excluded
        path = scope["path"]
        if any(path.startswith(exclude) for exclude in self.exclude_paths):
            await self.app(scope, receive, send)
            return
        
        # Authentication logic would go here
        # For now, we're just passing through
        await self.app(scope, receive, send)


def add_cors_middleware(app):
    """Add CORS middleware to the application.
    
    Args:
        app: FastAPI application
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_origin_regex=None,
        expose_headers=[],
        max_age=600,
    )
    logger.info("CORS middleware added")


def add_core_middleware(app):
    """Add all core middleware to the application.
    
    Args:
        app: FastAPI application
    """
    # Add CORS middleware
    add_cors_middleware(app)
    
    # Add logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Add auth middleware
    app.add_middleware(AuthMiddleware)
    
    logger.info("Core middleware added")
