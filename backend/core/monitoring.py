# backend/core/monitoring.py - MCP Server Monitoring
"""
Simple monitoring for tracking MCP server usage.
Provides counters for requests to main vs fallback servers.
"""

import logging
from typing import Dict, Optional
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class MCPMonitoring:
    """Simple monitoring for MCP server usage tracking."""
    
    def __init__(self):
        """Initialize monitoring counters."""
        self._lock = Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._tool_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._status_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        logger.debug("MCPMonitoring initialized")
    
    def increment_request(
        self, 
        server_type: str, 
        tool_name: Optional[str] = None, 
        status: str = "success"
    ) -> None:
        """Increment request counter.
        
        Args:
            server_type: 'main' or 'fallback'
            tool_name: Name of the tool being called (optional)
            status: Status of the request ('success', 'error', 'rate_limited', etc.)
        """
        with self._lock:
            # Increment overall counter
            self._counters[server_type] += 1
            
            # Increment tool-specific counter
            if tool_name:
                self._tool_counters[server_type][tool_name] += 1
            
            # Increment status-specific counter
            self._status_counters[server_type][status] += 1
            
            logger.debug(f"MCP request tracked: {server_type}, {tool_name}, {status}")
    
    def get_counts(self) -> Dict[str, Dict[str, int]]:
        """Get current monitoring counts.
        
        Returns:
            Dictionary with server_type as keys and counters as values
        """
        with self._lock:
            return {
                "servers": dict(self._counters),
                "tools": {server: dict(tools) for server, tools in self._tool_counters.items()},
                "statuses": {server: dict(statuses) for server, statuses in self._status_counters.items()}
            }
    
    def reset_counts(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._counters.clear()
            self._tool_counters.clear()
            self._status_counters.clear()
            logger.debug("MCP monitoring counters reset")


# Global monitoring instance
_mcp_monitoring: Optional[MCPMonitoring] = None


def get_mcp_monitoring() -> MCPMonitoring:
    """Get the global MCP monitoring instance.
    
    Returns:
        MCPMonitoring singleton instance
    """
    global _mcp_monitoring
    if _mcp_monitoring is None:
        _mcp_monitoring = MCPMonitoring()
    return _mcp_monitoring


def increment_mcp_request(
    server_type: str, 
    tool_name: Optional[str] = None, 
    status: str = "success"
) -> None:
    """Convenience function to increment MCP request counter.
    
    Args:
        server_type: 'main' or 'fallback'
        tool_name: Name of the tool being called (optional)
        status: Status of the request ('success', 'error', 'rate_limited', etc.)
    """
    try:
        monitor = get_mcp_monitoring()
        monitor.increment_request(server_type, tool_name, status)
    except Exception as e:
        logger.warning(f"Failed to track MCP request: {e}")