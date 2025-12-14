"""Lightweight MCP server adapter.

This module tries to use the optional `mcp` package if available. If the
package or expected symbols aren't present, it provides a minimal, safe
fallback so `main.py` can still import and the application can run.

The fallback `AIToolboxMCPServer.handle_request` understands a small JSON
shape used for local testing and will route to `handle_tool_call`.
"""

from typing import List, Dict, Any, Optional, Union
import json
import logging

# Import validators for input validation
from backend.mcp.mcp_validators import (
    SearchKnowledgeArgs,
    CreateTaskArgs,
    GetTaskStatsArgs
)

# Import rate limiter for protection against abuse
from backend.auth.mcp_rate_limiter import get_mcp_rate_limiter

# Import monitoring
from backend.core.monitoring import increment_mcp_request

logger = logging.getLogger(__name__)

try:
    # Optional dependency - only used when present and exposes the expected API
    from mcp import Server, NotificationOptions  # type: ignore
    from mcp.types import Tool, TextContent  # type: ignore
    MCP_AVAILABLE = True
except Exception:
    MCP_AVAILABLE = False

    # Define minimal local fallbacks so the rest of the code can run without the
    # MCP package. These are intentionally simple containers (not full feature
    # compatible) used only when the real library isn't installed or has a
    # different API surface.
    class Tool:
        def __init__(self, name: str, description: str = "", inputSchema: Optional[dict] = None):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema or {}

        def dict(self):
            return {"name": self.name, "description": self.description, "inputSchema": self.inputSchema}

    class TextContent:
        def __init__(self, type: str = "text", text: str = ""):
            self.type = type
            self.text = text


class AIToolboxMCPServer:
    """MCP adapter exposing a small set of tools.

    Methods:
    - initialize(): return a list of Tool-like objects (or dicts in fallback).
    - handle_tool_call(tool_name, arguments): perform the operation and return
      a list of TextContent-like objects.
    - handle_request(payload): minimal dispatcher compatible with main.py's
      simple usage; accepts dict payloads used by lightweight clients.
    """

    def __init__(
        self,
        search_service: Optional[Any] = None,
        supabase_client: Optional[Any] = None,
        vector_service: Optional[Any] = None
    ):
        """Initialize MCP server with injected dependencies.
        
        Args:
            search_service: Search service instance (injected dependency)
            supabase_client: Supabase client instance (injected dependency)
            vector_service: Vector service instance (injected dependency)
        """
        self.search_service = search_service
        self.supabase_client = supabase_client
        self.vector_service = vector_service
        self.rate_limiter = get_mcp_rate_limiter()
        
        logger.info("AIToolboxMCPServer initialized with dependency injection")

    async def initialize(self) -> List[Tool]:
        """Return available tools (Tool objects or simple fallbacks).

        The real `mcp` package may expect actual `Tool` instances; when using
        the fallback we return our local `Tool` wrappers.
        """
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

        # When the real MCP package is available, it may expect real Tool
        # instances; otherwise we return our simple wrappers.
        return tools

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any], identifier: str = "unknown") -> List[TextContent]:
        """Execute a named tool and return a list of TextContent-like objects.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            identifier: Identifier for rate limiting (IP, session ID, etc.)

        Returns:
            List of TextContent results
        """
        # Track this request as coming from the main server
        increment_mcp_request("main", tool_name)
        
        # Rate limiting check
        is_allowed, rate_info = self.rate_limiter.is_allowed(tool_name, identifier)
        if not is_allowed:
            error_msg = (
                f"Rate limit exceeded for {tool_name}. "
                f"Limit: {rate_info['limit']}, Window: {rate_info['window']}s. "
                f"Try again in {int(rate_info['reset_in'])} seconds."
            )
            logger.warning(f"Rate limit exceeded for {tool_name} from {identifier}")
            return [TextContent(type="text", text=error_msg)]

        # Validate dependencies are available
        if self.search_service is None or self.supabase_client is None:
            logger.warning("Required services not available for MCP tool call")
            return [TextContent(type="text", text="Services not available")]

        try:
            if tool_name == "search_knowledge":
                # Validate arguments using Pydantic model
                try:
                    validated_args = SearchKnowledgeArgs(**arguments)
                except Exception as e:
                    return [TextContent(type="text", text=f"Invalid arguments: {str(e)}")]

                # Use the search service to perform the search
                result = await self.search_service.smart_search(
                    query=validated_args.query,
                    context=validated_args.source,
                    max_total_results=validated_args.max_results
                )
                text = json.dumps(result, indent=2)
                return [TextContent(type="text", text=text)]

            if tool_name == "create_task":
                # Validate arguments using Pydantic model
                try:
                    validated_args = CreateTaskArgs(**arguments)
                except Exception as e:
                    return [TextContent(type="text", text=f"Invalid arguments: {str(e)}")]

                # Create a task in the database
                task_data = {
                    "name": validated_args.name,
                    "description": validated_args.description,
                    "status": "Not Started",
                    "progress": 0,
                    "priority": validated_args.priority.capitalize(),
                }
                
                # Insert into Supabase
                resp = self.supabase_client.table("tasks").insert(task_data).execute()
                task = (resp.data or [{}])[0]
                
                # Try to publish the task creation event
                try:
                    from backend.utils.sanitization import sanitize_for_display
                    # Note: publish function would need to be imported or injected
                    # publish("tasks", {"type": "created", "task": task})
                except Exception:
                    logger.debug("Failed to publish task creation (optional)")

                return [TextContent(type="text", text=f"Task created: {task.get('name', 'Unknown')} (id={task.get('id', 'Unknown')})")]

            if tool_name == "get_task_stats":
                # Validate arguments using Pydantic model (no args for this tool)
                try:
                    GetTaskStatsArgs(**arguments)
                except Exception as e:
                    return [TextContent(type="text", text=f"Invalid arguments: {str(e)}")]

                # Get task statistics
                resp = self.supabase_client.table("tasks").select("status").execute()
                counts: Dict[str, int] = {}
                for row in resp.data or []:
                    s = row.get("status", "unknown")
                    counts[s] = counts.get(s, 0) + 1
                text = "\n".join(f"- {k}: {v}" for k, v in counts.items())
                return [TextContent(type="text", text=f"Task Stats:\n{text}")]

            # Track unknown tool
            try:
                from backend.core.monitoring import increment_mcp_request
                increment_mcp_request("main", tool_name, "unknown_tool")
            except Exception:
                pass
            return [TextContent(type="text", text=f"Unknown tool: {tool_name}")]

        except Exception as e:
            logger.exception("Error executing MCP tool call")
            # Track error
            try:
                from backend.core.monitoring import increment_mcp_request
                increment_mcp_request("main", tool_name, "error")
            except Exception:
                pass
            return [TextContent(type="text", text=f"Tool error: {str(e)}")]

    async def handle_request(self, payload: Dict[str, Any]) -> Any:
        """Minimal request dispatcher used by `main.py`.

        Expected (fallback) payload shapes:
        - {'action': 'initialize'} -> returns tool list
        - {'action': 'call', 'tool': 'name', 'arguments': {...}} -> returns tool result

        If the real MCP library is present, you can ignore this and let the
        library create its own server wiring.
        """
        action = payload.get("action") or payload.get("type")
        
        # initialization
        if action == "initialize":
            tools = await self.initialize()
            # Convert Tool wrappers to simple dicts for JSON-serializable responses
            return [t.dict() if hasattr(t, "dict") else t for t in tools]

        # tool invocation
        if action == "call" or payload.get("tool"):
            tool_name = payload.get("tool") or payload.get("tool_name") or payload.get("name")
            arguments = payload.get("arguments") or payload.get("args") or {}
            
            # Get identifier for rate limiting (could be IP, session ID, etc.)
            identifier = payload.get("identifier", "unknown")
            
            results = await self.handle_tool_call(tool_name, arguments, identifier)
            return [{"type": tc.type, "text": tc.text} for tc in results]

        # Unknown / unhandled payload -> echo for debugging
        return {"error": "unsupported payload", "received": payload}