# backend/api/routes/logs.py - Log Endpoints
"""
Log management API endpoints.
"""

from fastapi import APIRouter, Depends
from typing import List, Optional
from pydantic import BaseModel
import logging

from backend.auth.security import verify_api_key_dependency
from backend.core.dependencies import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])

class LogEntry(BaseModel):
    id: str
    level: str
    message: str
    source: str
    timestamp: str
    component: Optional[str] = None

class LogsResponse(BaseModel):
    logs: List[LogEntry]

@router.get("/", response_model=LogsResponse, dependencies=[Depends(verify_api_key_dependency)])
async def get_logs(supabase_client = Depends(get_supabase_client)):
    """Get recent logs."""
    try:
        logger.info("Fetching logs from database")
        
        # Fetch logs from the database
        if supabase_client:
            response = supabase_client.table("logs").select("*").order("time", desc=True).limit(100).execute()
            logs_data = response.data if response and hasattr(response, 'data') else []
            
            # Convert to the expected format
            formatted_logs = []
            for log in logs_data:
                formatted_logs.append({
                    "id": str(log.get("id", "")),
                    "level": log.get("level", "INFO"),
                    "message": log.get("message", ""),
                    "source": log.get("source", "system"),
                    "timestamp": log.get("time", ""),
                    "component": log.get("component")
                })
            
            logger.info(f"Successfully fetched {len(formatted_logs)} logs")
            return LogsResponse(logs=formatted_logs)
        else:
            logger.warning("Supabase client not available")
            return LogsResponse(logs=[])
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        # Return empty logs instead of raising an exception to avoid breaking the frontend
        return LogsResponse(logs=[])