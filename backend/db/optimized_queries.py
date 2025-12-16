# backend/db/optimized_queries.py - Optimized Database Queries
"""
Optimized database queries with pagination, field selection, and performance improvements.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.core.dependencies import retry_supabase_operation

logger = logging.getLogger(__name__)


class OptimizedQueries:
    """Optimized database queries with pagination and field selection."""
    
    @staticmethod
    @retry_supabase_operation(max_retries=2)
    async def get_tasks_optimized(
        supabase_client,
        user_id: str = None,
        page: int = 1, 
        page_size: int = 20,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Optimized task query with pagination and field selection.
        
        Args:
            supabase_client: Initialized Supabase client
            user_id: Optional user ID filter
            page: Page number (1-indexed)
            page_size: Number of items per page
            filters: Additional filters (status, priority, etc.)
            
        Returns:
            Dict containing tasks and pagination info
        """
        try:
            # Build query with only necessary fields
            query = supabase_client.table("tasks").select(
                "id, name, status, progress, priority, created_at, updated_at, description"
            )
            
            # Add user filter if provided
            if user_id:
                query = query.eq("user_id", user_id)
            
            # Add other filters
            if filters:
                if filters.get("status"):
                    query = query.eq("status", filters["status"])
                if filters.get("priority"):
                    query = query.eq("priority", filters["priority"])
            
            # Calculate pagination
            start = (page - 1) * page_size
            end = start + page_size - 1
            
            # Execute query with ordering and pagination
            response = query \
                .order("created_at", desc=True) \
                .range(start, end) \
                .execute()
            
            tasks = response.data if response and hasattr(response, 'data') else []
            
            # Convert IDs to strings for consistency
            for task in tasks:
                if 'id' in task and isinstance(task['id'], int):
                    task['id'] = str(task['id'])
            
            return {
                "tasks": tasks,
                "page": page,
                "page_size": page_size,
                "has_more": len(tasks) == page_size,
                "total_count": len(tasks)
            }
            
        except Exception as e:
            logger.error(f"Error in optimized task query: {e}")
            return {
                "tasks": [],
                "page": page,
                "page_size": page_size,
                "has_more": False,
                "total_count": 0,
                "error": f"Query failed: {str(e)}"
            }
    
    @staticmethod
    @retry_supabase_operation(max_retries=2)
    async def get_chat_history_optimized(
        supabase_client,
        user_id: str = None,
        session_id: str = None,
        limit: int = 20,
        before_id: str = None
    ) -> Dict[str, Any]:
        """
        Optimized chat history query with cursor-based pagination.
        
        Args:
            supabase_client: Initialized Supabase client
            user_id: Optional user ID filter
            session_id: Optional session ID filter
            limit: Maximum number of messages to return
            before_id: Cursor for pagination (get messages before this ID)
            
        Returns:
            Dict containing messages and pagination info
        """
        try:
            # Build query with only necessary fields
            query = supabase_client.table("chat_history").select(
                "id, role, content, created_at, tools_used, user_id, session_id"
            )
            
            # Add filters
            if user_id:
                query = query.eq("user_id", user_id)
            
            if session_id:
                query = query.eq("session_id", session_id)
            
            if before_id:
                # Cursor-based pagination: get records before this ID
                query = query.lt("id", before_id)
            
            # Execute query with ordering and limit
            response = query \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            
            messages = response.data if response and hasattr(response, 'data') else []
            
            # Reverse order so newest messages appear last (for proper chat display)
            messages.reverse()
            
            return {
                "messages": messages,
                "has_more": len(messages) == limit,
                "last_id": messages[0]["id"] if messages else None,
                "total_count": len(messages)
            }
            
        except Exception as e:
            logger.error(f"Error in optimized chat history query: {e}")
            return {
                "messages": [],
                "has_more": False,
                "last_id": None,
                "total_count": 0,
                "error": f"Query failed: {str(e)}"
            }