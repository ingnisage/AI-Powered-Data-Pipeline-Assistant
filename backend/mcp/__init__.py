# backend/mcp/__init__.py
"""MCP (Model Coordination Protocol) server and validation components."""

from .mcp_server import AIToolboxMCPServer as MainMCPServer
from .mcp_server_fallback import AIToolboxMCPServer as FallbackMCPServer
from .mcp_validators import (
    SearchKnowledgeArgs,
    CreateTaskArgs,
    GetTaskStatsArgs
)

__all__ = [
    "MainMCPServer",
    "FallbackMCPServer",
    "SearchKnowledgeArgs",
    "CreateTaskArgs",
    "GetTaskStatsArgs",
]