"""Fallback MCP server adapter used when the project's `mcp_server.py` is unavailable or invalid.

This module contains a lightweight, resilient adapter that:
1. Uses NO imports from main.py or core.dependencies at module level (avoids circular imports)
2. Uses lazy imports inside methods to prevent import-time failures
3. Validates all inputs before use to prevent KeyError crashes
4. Provides descriptive error messages for debugging
5. Implements rate limiting for consistency with main MCP server
"""

from typing import List, Dict, Any, Optional, Union
import json
import logging

# Only import standard library modules at module level to ensure resilience
logger = logging.getLogger(__name__)

# We deliberately do not import the real `mcp` package or any project modules here;
# this file is a resilient fallback for local development and testing.


class Tool:
    """Minimal Tool class for fallback MCP server."""
    
    def __init__(self, name: str, description: str = "", inputSchema: Optional[dict] = None):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema or {}

    def dict(self):
        """Convert tool to dictionary representation."""
        return {"name": self.name, "description": self.description, "inputSchema": self.inputSchema}


class TextContent:
    """Minimal TextContent class for fallback MCP server."""
    
    def __init__(self, type: str = "text", text: str = ""):
        self.type = type
        self.text = text


class AIToolboxMCPServer:
    """Resilient fallback MCP server that avoids circular imports and validates inputs."""
    
    def __init__(self):
        """Initialize fallback MCP server."""
        logger.info("Fallback AIToolboxMCPServer initialized")
    
    async def initialize(self) -> List[Tool]:
        """Initialize available tools with proper schemas."""
        tools = [
            Tool(
                name="search_knowledge",
                description=(
                    "Search StackOverflow, GitHub, and official docs. Results are cached "
                    "in your private vector DB."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string", 
                            "description": "Search query",
                            "minLength": 1,
                            "maxLength": 500
                        },
                        "source": {
                            "type": "string",
                            "enum": ["all", "stackoverflow", "github", "official_doc"],
                            "default": "all",
                        },
                        "max_results": {
                            "type": "integer", 
                            "minimum": 1, 
                            "maximum": 10, 
                            "default": 5
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="create_task",
                description="Create a task in your real-time task board",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 200
                        },
                        "description": {
                            "type": "string",
                            "maxLength": 1000
                        },
                        "priority": {
                            "type": "string", 
                            "enum": ["low", "medium", "high"], 
                            "default": "medium"
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="get_task_stats",
                description="Get current task statistics",
                inputSchema={
                    "type": "object", 
                    "properties": {}, 
                    "required": []
                },
            ),
        ]
        return tools

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any], identifier: str = "unknown") -> List[TextContent]:
        """Handle tool calls with lazy imports and input validation.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            identifier: Identifier for rate limiting (IP, session ID, etc.)
            
        Returns:
            List of TextContent results
        """
        # Check rate limits first (fail fast)
        try:
            from backend.auth.fallback_rate_limiter import get_fallback_mcp_rate_limiter
            rate_limiter = get_fallback_mcp_rate_limiter()
            is_allowed, rate_info = rate_limiter.is_allowed(tool_name, identifier)
            
            if not is_allowed:
                error_msg = (
                    f"Rate limit exceeded for {tool_name}. "
                    f"Limit: {rate_info['limit']}, Window: {rate_info['window']}s. "
                    f"Try again in {rate_info['reset_in']} seconds."
                )
                logger.warning(f"Rate limit exceeded for {tool_name} from {identifier}")
                # Track rate limited request
                try:
                    from backend.core.monitoring import increment_mcp_request
                    increment_mcp_request("fallback", tool_name, "rate_limited")
                except Exception:
                    pass  # Continue even if monitoring fails
                return [TextContent(type="text", text=error_msg)]
        except ImportError:
            # If rate limiter is not available, continue without it
            logger.debug("Rate limiter not available, continuing without rate limiting")
        except Exception as e:
            # If rate limiter fails, continue without it to maintain resilience
            logger.warning(f"Rate limiter error, continuing without rate limiting: {e}")
        
        # Track this request as coming from the fallback server
        try:
            from backend.core.monitoring import increment_mcp_request
            increment_mcp_request("fallback", tool_name)
        except Exception:
            pass  # Continue even if monitoring fails
        
        # Lazy import dependencies only when needed to avoid circular imports
        try:
            # Lazy import to avoid circular dependencies
            from backend.core.dependencies import get_search_service, get_supabase_client
        except ImportError:
            logger.warning("Could not import backend.core.dependencies - using fallback")
            # Try alternative import paths
            try:
                from core.dependencies import get_search_service, get_supabase_client
            except ImportError:
                logger.error("Failed to import dependencies for MCP fallback")
                return [TextContent(type="text", text="Service dependencies not available")]
        
        # Get services with error handling
        try:
            search_service = get_search_service()
            supabase = get_supabase_client()
            
            if search_service is None or supabase is None:
                return [TextContent(type="text", text="Required services not initialized")]
        except Exception as e:
            logger.error(f"Error getting services: {e}")
            return [TextContent(type="text", text=f"Service initialization error: {str(e)}")]

        try:
            # Validate inputs before use to prevent KeyError
            if tool_name == "search_knowledge":
                # Validate required arguments
                query = arguments.get("query")
                if not query:
                    return [TextContent(type="text", text="Error: 'query' argument is required for search_knowledge")]
                
                if not isinstance(query, str) or len(query.strip()) == 0:
                    return [TextContent(type="text", text="Error: 'query' must be a non-empty string")]
                
                # Validate optional arguments with defaults
                source = arguments.get("source", "all")
                if source not in ["all", "stackoverflow", "github", "official_doc"]:
                    return [TextContent(type="text", text="Error: 'source' must be one of: all, stackoverflow, github, official_doc")]
                
                max_results = arguments.get("max_results", 5)
                if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
                    return [TextContent(type="text", text="Error: 'max_results' must be an integer between 1 and 10")]
                
                # Perform the search with error handling
                try:
                    result = await search_service.smart_search(
                        query=query.strip(),
                        context=source,
                        max_total_results=max_results
                    )
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                except Exception as e:
                    logger.error(f"Error in search_knowledge: {e}")
                    # Track error
                    try:
                        from backend.core.monitoring import increment_mcp_request
                        increment_mcp_request("fallback", tool_name, "error")
                    except Exception:
                        pass
                    return [TextContent(type="text", text=f"Search error: {str(e)}")]

            elif tool_name == "create_task":
                # Validate required arguments
                name = arguments.get("name")
                if not name:
                    return [TextContent(type="text", text="Error: 'name' argument is required for create_task")]
                
                if not isinstance(name, str) or len(name.strip()) == 0:
                    return [TextContent(type="text", text="Error: 'name' must be a non-empty string")]
                
                # Validate optional arguments
                description = arguments.get("description", "")
                if not isinstance(description, str):
                    return [TextContent(type="text", text="Error: 'description' must be a string")]
                
                priority = arguments.get("priority", "medium")
                if priority not in ["low", "medium", "high"]:
                    return [TextContent(type="text", text="Error: 'priority' must be one of: low, medium, high")]
                
                # Create task with error handling
                try:
                    task_data = {
                        "name": name.strip(),
                        "description": description,
                        "status": "Not Started",
                        "progress": 0,
                        "priority": priority.capitalize(),
                    }
                    
                    resp = supabase.table("tasks").insert(task_data).execute()
                    task = (resp.data or [{}])[0]
                    
                    task_name = task.get('name', 'Unknown')
                    task_id = task.get('id', 'Unknown')
                    return [TextContent(type="text", text=f"Task created: {task_name} (id={task_id})")]
                except Exception as e:
                    logger.error(f"Error in create_task: {e}")
                    # Track error
                    try:
                        from backend.core.monitoring import increment_mcp_request
                        increment_mcp_request("fallback", tool_name, "error")
                    except Exception:
                        pass
                    return [TextContent(type="text", text=f"Task creation error: {str(e)}")]

            elif tool_name == "get_task_stats":
                # No arguments needed for this tool, but validate anyway
                try:
                    resp = supabase.table("tasks").select("status").execute()
                    counts: Dict[str, int] = {}
                    for row in resp.data or []:
                        s = row.get("status", "unknown")
                        counts[s] = counts.get(s, 0) + 1
                    text = "\n".join(f"- {k}: {v}" for k, v in counts.items())
                    return [TextContent(type="text", text=f"Task Stats:\n{text}")]
                except Exception as e:
                    logger.error(f"Error in get_task_stats: {e}")
                    # Track error
                    try:
                        from backend.core.monitoring import increment_mcp_request
                        increment_mcp_request("fallback", tool_name, "error")
                    except Exception:
                        pass
                    return [TextContent(type="text", text=f"Stats error: {str(e)}")]

            else:
                # Handle unknown tool with descriptive error message
                # Track unknown tool
                try:
                    from backend.core.monitoring import increment_mcp_request
                    increment_mcp_request("fallback", tool_name, "unknown_tool")
                except Exception:
                    pass
                return [TextContent(type="text", text=f"Unknown tool: '{tool_name}'. Available tools: search_knowledge, create_task, get_task_stats")]

        except Exception as e:
            logger.exception("Unexpected error executing MCP tool call")
            # Track unexpected error
            try:
                from backend.core.monitoring import increment_mcp_request
                increment_mcp_request("fallback", tool_name if 'tool_name' in locals() else "unknown", "unexpected_error")
            except Exception:
                pass
            return [TextContent(type="text", text=f"Unexpected tool error: {str(e)}. Please check the tool name and arguments.")]

    async def handle_request(self, payload: Dict[str, Any]) -> Any:
        """Handle incoming requests with proper error handling.
        
        Args:
            payload: Request payload
            
        Returns:
            Response data
        """
        # Validate payload
        if not isinstance(payload, dict):
            return {"error": "Invalid payload format", "received": str(payload)}
        
        action = payload.get("action") or payload.get("type")
        
        # Handle initialization
        if action == "initialize":
            try:
                tools = await self.initialize()
                return [t.dict() if hasattr(t, "dict") else t for t in tools]
            except Exception as e:
                logger.error(f"Error initializing tools: {e}")
                return {"error": f"Initialization failed: {str(e)}"}

        # Handle tool calls
        elif action == "call" or payload.get("tool"):
            tool_name = payload.get("tool") or payload.get("tool_name") or payload.get("name")
            arguments = payload.get("arguments") or payload.get("args") or {}
            
            # Validate tool_name
            if not tool_name:
                return {"error": "No tool specified", "received": payload}
            
            try:
                # Get identifier for rate limiting (could be IP, session ID, etc.)
                identifier = payload.get("identifier", "unknown")
                results = await self.handle_tool_call(tool_name, arguments, identifier)
                return [{"type": tc.type, "text": tc.text} for tc in results]
            except Exception as e:
                logger.error(f"Error handling tool call: {e}")
                return {"error": f"Tool call failed: {str(e)}", "tool": tool_name}

        # Handle unknown actions
        else:
            return {
                "error": f"Unsupported action: '{action}'. Supported actions: initialize, call", 
                "received": payload
            }