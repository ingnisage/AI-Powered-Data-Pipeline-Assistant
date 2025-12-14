# tools/executor.py - Modular Tool Executor
"""
Unified tool executor that dispatches to appropriate tool handlers.
Replaces the monolithic ToolExecutor class with a modular architecture.
"""

import logging
from typing import Dict, Any, Optional
from .base import BaseTool, ToolResult
from .data_tools import QueryDataSourceTool, AnalyzeDataQualityTool, GenerateSQLQueryTool
from .search_tools import SmartSearchTool, QueryKnowledgeBaseTool, ReadChatHistoryTool
from .pipeline_tools import ScheduleDataPipelineTool, TriggerDataPipelineTool
from .tool_registry import get_tool_registry, ToolRole

logger = logging.getLogger(__name__)


class ModularToolExecutor:
    """Modular tool executor with dependency injection and clean separation of concerns."""
    
    def __init__(
        self,
        openai_client=None,
        search_service=None,
        vector_service=None,
        supabase_client=None
    ):
        """Initialize tool executor with service dependencies.
        
        Args:
            openai_client: OpenAI client for LLM-based tools
            search_service: Search service for smart search
            vector_service: Vector service for knowledge base queries
            supabase_client: Supabase client for database operations
        """
        self.openai_client = openai_client
        self.search_service = search_service
        self.vector_service = vector_service
        self.supabase_client = supabase_client
        
        # Tool registry for metadata
        self.registry = get_tool_registry()
        
        # Initialize tool handlers
        self._handlers: Dict[str, BaseTool] = {}
        self._register_handlers()
        
        logger.info(f"ModularToolExecutor initialized with {len(self._handlers)} tool handlers")
    
    def _register_handlers(self) -> None:
        """Register all tool handlers."""
        
        # Data tools
        self._handlers["query_data_source"] = QueryDataSourceTool()
        self._handlers["analyze_data_quality"] = AnalyzeDataQualityTool()
        self._handlers["generate_sql_query"] = GenerateSQLQueryTool(self.openai_client)
        
        # Search tools
        self._handlers["smart_search"] = SmartSearchTool(self.search_service)
        self._handlers["query_knowledge_base"] = QueryKnowledgeBaseTool(self.vector_service)
        self._handlers["read_chat_history"] = ReadChatHistoryTool(self.supabase_client)
        
        # Pipeline tools
        self._handlers["schedule_data_pipeline"] = ScheduleDataPipelineTool()
        self._handlers["trigger_data_pipeline"] = TriggerDataPipelineTool()
    
    def is_tool_allowed(self, user_role: str, tool_name: str) -> bool:
        """Check if user role has permission to use the tool.
        
        Args:
            user_role: User's role
            tool_name: Name of the tool to check
            
        Returns:
            True if tool is allowed for the role
        """
        tool_def = self.registry.get(tool_name)
        if not tool_def:
            return False
        
        # General tools available to all
        if tool_def.required_role == ToolRole.GENERAL:
            return True
        
        # Check if user role matches required role
        try:
            user_role_enum = ToolRole(user_role)
            return user_role_enum == tool_def.required_role
        except ValueError:
            return False
    
    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_role: str = "general"
    ) -> Dict[str, Any]:
        """Execute a tool call with authorization and safety checks.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            user_role: User's role for authorization
            
        Returns:
            Dictionary with tool execution results
        """
        logger.info(f"Executing tool: {tool_name} for role: {user_role}")
        
        # Authorization check
        if not self.is_tool_allowed(user_role, tool_name):
            logger.warning(f"Tool '{tool_name}' not allowed for role '{user_role}'")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not allowed for role '{user_role}'",
                "tool_name": tool_name
            }
        
        # Get tool handler
        handler = self._handlers.get(tool_name)
        if not handler:
            logger.error(f"Unknown tool: {tool_name}")
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "tool_name": tool_name
            }
        
        # Execute tool with safety wrapper
        try:
            result = await handler.execute_safe(**arguments)
            return result.to_dict()
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name
            }
    
    def get_available_tools(self, user_role: Optional[str] = None) -> list:
        """Get list of available tools, optionally filtered by role.
        
        Args:
            user_role: Optional role to filter tools
            
        Returns:
            List of available tool definitions
        """
        if user_role:
            try:
                role_enum = ToolRole(user_role)
                tools = self.registry.get_by_role(role_enum)
            except ValueError:
                # Invalid role, return general tools only
                tools = self.registry.get_by_role(ToolRole.GENERAL)
        else:
            tools = self.registry.get_all()
        
        return [tool.to_dict() for tool in tools]
    
    def get_tools_for_openai(self, user_role: Optional[str] = None) -> list:
        """Get tools in OpenAI function calling format.
        
        Args:
            user_role: Optional role to filter tools
            
        Returns:
            List of tool definitions in OpenAI format
        """
        if user_role:
            try:
                role_enum = ToolRole(user_role)
                tools = self.registry.get_by_role(role_enum)
            except ValueError:
                tools = self.registry.get_by_role(ToolRole.GENERAL)
        else:
            tools = self.registry.get_all()
        
        return [tool.to_openai_format() for tool in tools]


# Convenience function for backward compatibility
async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    executor: ModularToolExecutor
) -> Dict[str, Any]:
    """Execute a tool using the modular executor.
    
    Args:
        tool_name: Name of the tool
        arguments: Tool arguments
        executor: ModularToolExecutor instance
        
    Returns:
        Tool execution results
    """
    return await executor.execute_tool_call(tool_name, arguments)
