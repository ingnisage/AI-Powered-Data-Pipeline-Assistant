# backend/api/routes/monitoring.py - Monitoring Endpoint
"""Monitoring endpoint for MCP server usage tracking."""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from backend.core.monitoring import get_mcp_monitoring

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/mcp-stats")
async def get_mcp_statistics():
    """Get MCP server usage statistics.
    
    Returns:
        Dictionary with monitoring statistics
    """
    try:
        monitor = get_mcp_monitoring()
        stats = monitor.get_counts()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve statistics: {str(e)}"
        }


@router.post("/mcp-stats/reset")
async def reset_mcp_statistics():
    """Reset MCP server usage statistics.
    
    Returns:
        Confirmation of reset
    """
    try:
        monitor = get_mcp_monitoring()
        monitor.reset_counts()
        return {
            "status": "success",
            "message": "Statistics reset successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to reset statistics: {str(e)}"
        }