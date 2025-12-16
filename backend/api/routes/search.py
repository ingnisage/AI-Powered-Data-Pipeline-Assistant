# backend/api/routes/search.py - Search Endpoints
"""
Search functionality API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from backend.models.interaction import SearchRequest
from backend.auth.security import verify_api_key_dependency
from backend.core.dependencies import get_search_service

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/", dependencies=[Depends(verify_api_key_dependency)])
async def search_endpoint(
    request: SearchRequest,
    search_service = Depends(get_search_service)
):
    """Perform search across knowledge sources.
    
    Args:
        request: Search request with source, query, and max_results
        
    Returns:
        Dictionary with search results and metadata
    """
    try:
        # Perform smart search
        results = await search_service.smart_search(
            query=request.query,
            source=request.source,
            max_results=request.max_results or 3
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")