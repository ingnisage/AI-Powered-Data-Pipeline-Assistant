# backend/auth/rate_limiting.py - Rate Limiting (Deprecated)
"""
Rate limiting implementation for API protection.

NOTE: This module is currently not used in the codebase. Consider using it for general
API endpoint protection or integrate it with authentication middleware if needed.
"""

import time
import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()
        logger.info("RateLimiter initialized")
    
    def is_allowed(
        self,
        identifier: str,
        max_requests: int = 60,
        window_seconds: int = 60
    ) -> Tuple[bool, Dict[str, int]]:
        """Check if request is within rate limits.
        
        Args:
            identifier: Unique identifier (IP, API key, etc.)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        with self._lock:
            current_time = time.time()
            
            # Clean old requests outside the window
            self._requests[identifier] = [
                req_time for req_time in self._requests[identifier]
                if current_time - req_time < window_seconds
            ]
            
            # Check if within limits
            request_count = len(self._requests[identifier])
            is_allowed = request_count < max_requests
            
            # Add current request if allowed
            if is_allowed:
                self._requests[identifier].append(current_time)
            
            # Calculate rate limit info
            remaining = max(0, max_requests - request_count)
            reset_time = current_time + window_seconds
            
            rate_limit_info = {
                "limit": max_requests,
                "remaining": remaining,
                "reset": int(reset_time)
            }
            
            if not is_allowed:
                logger.warning(f"Rate limit exceeded for: {identifier}")
            
            return is_allowed, rate_limit_info
    
    def get_stats(self, identifier: str) -> Dict[str, int]:
        """Get rate limit statistics for an identifier.
        
        Args:
            identifier: Unique identifier
            
        Returns:
            Rate limit statistics
        """
        with self._lock:
            current_time = time.time()
            recent_requests = [
                req_time for req_time in self._requests[identifier]
                if current_time - req_time < 60
            ]
            
            return {
                "requests_last_minute": len(recent_requests),
                "total_requests": len(self._requests[identifier])
            }
    
    def reset_identifier(self, identifier: str) -> None:
        """Reset rate limit for an identifier.
        
        Args:
            identifier: Unique identifier
        """
        with self._lock:
            if identifier in self._requests:
                del self._requests[identifier]
                logger.info(f"Rate limit reset for: {identifier}")


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance.
    
    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
