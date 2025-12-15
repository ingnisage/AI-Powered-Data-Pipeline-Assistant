# tools/search_tools.py - Search and Knowledge Tools
"""
Tool handlers for search and knowledge base queries.
"""

from typing import Optional, Dict, Any
from .base import BaseTool, ToolResult


class SmartSearchTool(BaseTool):
    """Tool for intelligent search across multiple sources."""
    
    def __init__(self, search_service=None):
        super().__init__(name="smart_search", category="search")
        self.search_service = search_service
    
    async def execute(
        self,
        query: str,
        context: str = "all",
        source: Optional[str] = None,
        max_total_results: int = 5,
        **kwargs
    ) -> ToolResult:
        """Execute smart search across knowledge sources.
        
        Args:
            query: Search query
            context: Context type (error, code_example, documentation, best_practice, all)
            source: Optional source restriction (github, stackoverflow, official_doc, spark_docs)
            max_total_results: Maximum results to return
            
        Returns:
            ToolResult with search results
        """
        # Validate parameters
        error = self.validate_params(['query'], {'query': query})
        if error:
            return ToolResult(success=False, error=error)
        
        if not self.search_service:
            return ToolResult(
                success=False,
                error="Search service not configured"
            )
        
        try:
            # Map context to source if needed (maintain backward compatibility)
            if source is None and context != "all":
                source_mapping = {
                    "error": "stackoverflow",
                    "code_example": "github",
                    "documentation": "official_doc",
                    "best_practice": "official_doc"
                }
                source = source_mapping.get(context)
            
            # Execute search using search service with correct parameter names
            results = await self.search_service.smart_search(
                query=query,
                source=source or "all",
                max_results=max_total_results  # Map max_total_results to max_results
            )
            
            data = {
                "query": query,
                "context": context,
                "source": source,
                "results": results.get("results", []),
                "total_results": results.get("total_results", 0)
            }
            
            return ToolResult(success=True, data=data)
            
        except Exception as e:
            self.logger.error(f"Smart search failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Search failed: {str(e)}"
            )


class QueryKnowledgeBaseTool(BaseTool):
    """Tool for direct vector search in knowledge base."""
    
    def __init__(self, vector_service=None):
        super().__init__(name="query_knowledge_base", category="knowledge")
        self.vector_service = vector_service
    
    async def execute(
        self,
        query: str,
        top_k: int = 5,
        **kwargs
    ) -> ToolResult:
        """Execute vector search in knowledge base.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            ToolResult with knowledge base results
        """
        # Validate parameters
        error = self.validate_params(['query'], {'query': query})
        if error:
            return ToolResult(success=False, error=error)
        
        if not self.vector_service:
            return ToolResult(
                success=False,
                error="Vector service not configured"
            )
        
        try:
            # Execute vector search
            results = await self.vector_service.search(
                query=query,
                top_k=top_k
            )
            
            data = {
                "query": query,
                "top_k": top_k,
                "results": results,
                "total_results": len(results)
            }
            
            return ToolResult(success=True, data=data)
            
        except Exception as e:
            self.logger.error(f"Knowledge base query failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Knowledge base query failed: {str(e)}"
            )


class ReadChatHistoryTool(BaseTool):
    """Tool for reading chat history."""
    
    def __init__(self, supabase_client=None):
        super().__init__(name="read_chat_history", category="chat")
        self.supabase_client = supabase_client
    
    async def execute(
        self,
        session_id: Optional[str] = None,
        limit: int = 20,
        **kwargs
    ) -> ToolResult:
        """Read recent chat history.
        
        Args:
            session_id: Optional session ID filter
            limit: Maximum number of messages to return
            
        Returns:
            ToolResult with chat history
        """
        if not self.supabase_client:
            return ToolResult(
                success=False,
                error="Database not configured"
            )
        
        try:
            query = self.supabase_client.table("chat_history").select("*")
            
            if session_id:
                query = query.eq("session_id", session_id)
            
            query = query.order("created_at", desc=True).limit(limit)
            response = query.execute()
            
            data = {
                "session_id": session_id,
                "messages": response.data,
                "total_messages": len(response.data)
            }
            
            return ToolResult(success=True, data=data)
            
        except Exception as e:
            self.logger.error(f"Failed to read chat history: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Chat history read failed: {str(e)}"
            )