from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from backend.core.dependencies import lifespan, get_service_health
from backend.utils.logging_sanitizer import SanitizingHandler, get_sanitizer
# Import Render configuration
from backend.core.render_config import configure_for_render

# Configure logging with sanitization
logging.basicConfig(level=logging.INFO)

# Wrap all existing handlers with sanitizing handlers for global redaction
root_logger = logging.getLogger()
sanitizer = get_sanitizer()

# Store original handlers and replace them with sanitizing wrappers
original_handlers = list(root_logger.handlers)
root_logger.handlers.clear()

for handler in original_handlers:
    sanitizing_handler = SanitizingHandler(handler, sanitizer)
    root_logger.addHandler(sanitizing_handler)

logger = logging.getLogger(__name__)

# Log environment information
logger.info(f"ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
logger.info(f"BACKEND_API_KEY: {'set' if os.getenv('BACKEND_API_KEY') else 'not set'}")

# Create FastAPI app with lifespan for proper service management
app = FastAPI(
    title="AI Workbench Backend",
    description="Backend API for AI Workbench - Data Pipeline Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Apply Render-specific optimizations if running on Render
configure_for_render(app)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"]  # Expose custom headers if needed
)

@app.get("/")
async def root():
    """Root endpoint - basic health check."""
    return {"message": "AI Workbench Backend Running 🚀"}

# Note: Health check endpoint is now managed by Render configuration
# The Render configuration will register the appropriate health check endpoint

# Include routers from different modules
from backend.api.routes import chat, logs, search, tasks, monitoring

app.include_router(chat.router)
app.include_router(logs.router)
app.include_router(search.router)
app.include_router(tasks.router)
app.include_router(monitoring.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)