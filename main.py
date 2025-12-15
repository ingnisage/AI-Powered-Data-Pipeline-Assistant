from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from backend.core.dependencies import lifespan, get_service_health

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app with lifespan for proper service management
app = FastAPI(
    title="AI Workbench Backend",
    description="Backend API for AI Workbench - Data Pipeline Assistant",
    version="1.0.0",
    lifespan=lifespan
)

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

@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    health_status = get_service_health()
    return {
        "status": "healthy" if health_status["overall"] else "unhealthy",
        "services": health_status["services"]
    }

# Include routers from different modules
from backend.api.routes import chat, logs, search, tasks

app.include_router(chat.router)
app.include_router(logs.router)
app.include_router(search.router)
app.include_router(tasks.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)