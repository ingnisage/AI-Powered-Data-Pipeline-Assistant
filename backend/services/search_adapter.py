# backend/services/search_adapter.py - Search Adapter
"""
Adapter that integrates the external search service with the backend dependency injection system.
"""

import logging
from typing import List, Dict, Any, Optional

# Import the existing search components
from backend.services.search_engine import SearchService as ExternalSearchService

logger = logging.getLogger(__name__)

class SearchAdapter:
    """Adapter for integrating external search service with backend dependency injection."""
    
    def __init__(self, openai_client=None, supabase_client=None):
        """Initialize search adapter with clients.
        
        Args:
            openai_client: OpenAI client for embeddings
            supabase_client: Supabase client for database operations
        """
        # Initialize the external search service with the provided clients
        self.external_search_service = ExternalSearchService(openai_client, supabase_client)
        
        logger.info("SearchAdapter initialized with external search components")
    
    async def smart_search(
        self,
        query: str,
        context: str = "all",
        source: Optional[str] = None,
        max_total_results: int = 5
    ) -> Dict[str, Any]:
        """Intelligently search across knowledge sources.
        
        Args:
            query: Search query
            context: Context type (error, code_example, documentation, best_practice, all)
            source: Optional source restriction (github, stackoverflow, official_doc)
            max_total_results: Maximum results to return
            
        Returns:
            Dictionary with search results and metadata
        """
        logger.info(f"Performing smart search: {query[:50]}...")
        
        try:
            # Use the external search service's async method
            if source:
                # If a specific source is requested, use the tool_search method
                result = await self.external_search_service.tool_search_async(
                    query, 
                    source_hint=source, 
                    max_results=max_total_results
                )
            else:
                # Otherwise use the smart search method
                result = await self.external_search_service.search_smart_async(
                    query, 
                    context=context, 
                    max_total_results=max_total_results
                )
            
            logger.info(f"Smart search completed with {len(result.get('results', []))} results")
            return result
            
        except Exception as e:
            logger.error(f"Error during smart search: {e}", exc_info=True)
            return {
                "results": [],
                "error": str(e),
                "message": "Search failed due to an unexpected error"
            }