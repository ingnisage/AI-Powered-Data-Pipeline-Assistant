# main.py - Main Application Entry Point
"""
Main FastAPI application with modular architecture.
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Add the project root to Python path to ensure proper imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import from backend modules
from backend.services.config import config
from backend.core.dependencies import lifespan
from backend.core.middleware import add_core_middleware
from backend.api import api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create FastAPI app with lifespan management
app = FastAPI(
    title="AI Workbench Backend",
    description="Modular backend for AI-powered data pipeline assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
add_core_middleware(app)

# Include API routers
app.include_router(api_router)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI Workbench Backend Running 🚀"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='AI Workbench Backend')
    parser.add_argument('--port', type=int, default=8000, help='Port to run the server on')
    args = parser.parse_args()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=args.port,
        reload=os.getenv("ENVIRONMENT") == "development"
    )