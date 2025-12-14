# backend/api/__init__.py - API Router
"""Main API router that includes all sub-routers."""

from fastapi import APIRouter

# Try absolute imports first, then fall back to relative imports
try:
    from backend.api.routes import chat, tasks, logs, search, monitoring
except ImportError:
    # Fallback to relative imports when running as script
    from .routes import chat, tasks, logs, search, monitoring

# Create main API router
api_router = APIRouter(prefix="/api")

# Include all sub-routers
api_router.include_router(chat.router)
api_router.include_router(tasks.router)
api_router.include_router(logs.router)
api_router.include_router(search.router)
api_router.include_router(monitoring.router)

__all__ = ["api_router"]