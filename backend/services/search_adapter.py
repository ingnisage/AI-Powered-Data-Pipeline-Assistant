# backend/services/search_adapter.py - Search Adapter
"""
Adapter that integrates the external search service with the backend dependency injection system.
"""

import logging
from typing import List, Dict, Any, Optional

# Import the existing search components
from backend.services.search_service import SearchService

logger = logging.getLogger(__name__)

class SearchAdapter:
    """Adapter for integrating external search service with backend dependency injection."""
    
    def __init__(self, openai_client=None, supabase_client=None):
        """Initialize search adapter with clients.
        
        Args:
            openai_client: OpenAI client for embeddings
            supabase_client: Supabase client for database operations
        """
        # Initialize the search service with the provided clients
        self.search_service = SearchService(openai_client, supabase_client)
        
        logger.info("SearchAdapter initialized with search service")
    
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
            source: Optional source restriction (github, stackoverflow, official_doc, spark_docs)
            max_total_results: Maximum results to return
            
        Returns:
            Dictionary with search results and metadata
        """
        logger.info(f"Performing smart search: {query[:50]}...")
        
        try:
            # Map context to source if needed (similar to SmartSearchTool)
            if source is None and context != "all":
                source_mapping = {
                    "error": "stackoverflow",
                    "code_example": "github",
                    "documentation": "official_doc",
                    "best_practice": "official_doc"
                }
                source = source_mapping.get(context)
            
            # Use the search service's smart_search method with correct parameters
            result = await self.search_service.smart_search(
                query=query,
                source=source or "all",
                max_results=max_total_results
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