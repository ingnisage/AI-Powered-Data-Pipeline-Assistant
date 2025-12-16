# backend/main.py - Main Application Entry Point
"""
Main entry point for the AI Workbench backend application.
Initializes FastAPI app and registers all routes.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging before other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Apply Render-specific optimizations early
try:
    from backend.core.render_config import configure_for_render
    IS_RENDER = configure_for_render()
    if IS_RENDER:
        logger.info("Render optimizations applied")
    else:
        logger.info("Running in non-Render environment")
except Exception as e:
    logger.warning(f"Failed to apply Render optimizations: {e}")
    IS_RENDER = False

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import routes
from backend.api.routes import tasks, chat, logs, search
from backend.core.dependencies import ServiceContainer
from backend.core.render_config import configure_for_render

# Health check import
try:
    from backend.core.render_config import _register_health_check_endpoint
except ImportError:
    _register_health_check_endpoint = None

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Create app instance
    app = FastAPI(
        title="AI Workbench Backend",
        description="Backend API for AI Workbench - Data Pipeline Assistant",
        version="2.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"]
    )
    
    # Register routes
    app.include_router(tasks.router)
    app.include_router(chat.router)
    app.include_router(logs.router)
    app.include_router(search.router)
    
    # Register health check endpoint for Render
    if IS_RENDER:
        try:
            configure_for_render(app)
            logger.info("Health check endpoint registered for Render")
        except Exception as e:
            logger.error(f"Failed to register health check endpoint: {e}")
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {"message": "AI Workbench Backend Running 🚀"}
    
    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the AI Workbench backend")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()
    
    logger.info(f"Starting AI Workbench backend on port {args.port}")
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=args.port,
        reload=True,
        log_level="info"
    )