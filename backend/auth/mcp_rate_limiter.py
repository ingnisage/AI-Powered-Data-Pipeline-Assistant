# backend/auth/mcp_rate_limiter.py - Rate Limiting for MCP Tools
"""
Rate limiting implementation for MCP tools to prevent abuse and protect resources.
"""

import time
import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class MCPRateLimiter:
    """Rate limiter for MCP tools to prevent resource exhaustion."""
    
    def __init__(self):
        """Initialize rate limiter with default limits."""
        # Store requests per tool per identifier (IP or session)
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()
        
        # Rate limits: (requests, time_window_seconds)
        self._limits = {
            "search_knowledge": (10, 60),  # 10 requests per minute
            "create_task": (5, 60),        # 5 requests per minute
            "get_task_stats": (30, 60),    # 30 requests per minute
        }
        
        logger.info("MCPRateLimiter initialized with default limits")
    
    def is_allowed(
        self, 
        tool_name: str, 
        identifier: str,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None
    ) -> Tuple[bool, Dict[str, int]]:
        """Check if a request for a tool is within rate limits.
        
        Args:
            tool_name: Name of the tool being called
            identifier: Unique identifier (IP, session ID, etc.)
            max_requests: Override default max requests
            window_seconds: Override default time window
            
        Returns:
            Tuple of (is_allowed, rate_info)
        """
        # Get limits for this tool
        default_max, default_window = self._limits.get(tool_name, (10, 60))
        max_req = max_requests or default_max
        window = window_seconds or default_window
        
        # Create unique key for this tool and identifier
        key = f"{tool_name}:{identifier}"
        current_time = time.time()
        
        with self._lock:
            # Remove expired requests
            self._requests[key] = [
                req_time for req_time in self._requests[key] 
                if current_time - req_time < window
            ]
            
            # Check if we're within limits
            request_count = len(self._requests[key])
            is_allowed = request_count < max_req
            
            # If allowed, record this request
            if is_allowed:
                self._requests[key].append(current_time)
            
            # Prepare rate info for response
            rate_info = {
                "limit": max_req,
                "remaining": max(0, max_req - request_count - (0 if is_allowed else 1)),
                "reset_in": window - (current_time - self._requests[key][0]) if self._requests[key] else 0,
                "window": window
            }
            
            return is_allowed, rate_info
    
    def get_limits(self) -> Dict[str, Tuple[int, int]]:
        """Get current rate limits for all tools.
        
        Returns:
            Dictionary mapping tool names to (max_requests, window_seconds)
        """
        return self._limits.copy()
    
    def set_limit(self, tool_name: str, max_requests: int, window_seconds: int) -> None:
        """Set rate limit for a specific tool.
        
        Args:
            tool_name: Name of the tool
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        """
        self._limits[tool_name] = (max_requests, window_seconds)
        logger.info(f"Rate limit for {tool_name} set to {max_requests}/{window_seconds}s")


# Global rate limiter instance
_mcp_rate_limiter: Optional[MCPRateLimiter] = None


def get_mcp_rate_limiter() -> MCPRateLimiter:
    """Get the global MCP rate limiter instance.
    
    Returns:
        MCPRateLimiter singleton instance
    """
    global _mcp_rate_limiter
    if _mcp_rate_limiter is None:
        _mcp_rate_limiter = MCPRateLimiter()
    return _mcp_rate_limiter