# backend/api/routes/search.py - Search Endpoints
"""
Search functionality API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from backend.models.interaction import SearchRequest
from backend.auth.security import verify_api_key_dependency
from backend.core.dependencies import get_openai_client, get_supabase_client

# Import the new search service
from backend.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/", dependencies=[Depends(verify_api_key_dependency)])
async def search_endpoint(
    request: SearchRequest,
    openai_client = Depends(get_openai_client),
    supabase_client = Depends(get_supabase_client)
):
    """Perform search across knowledge sources.
    
    Args:
        request: Search request with source, query, and max_results
        
    Returns:
        Dictionary with search results and metadata
    """
    try:
        # Initialize search service
        search_service = SearchService(openai_client, supabase_client)
        
        # Perform smart search
        results = await search_service.smart_search(
            query=request.query,
            source=request.source,
            max_results=request.max_results or 3
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")