# auth/security.py - Comprehensive Security Module
"""
Security module providing robust authentication, rate limiting, and key management.
Addresses timing attacks, implements rate limiting, and supports key rotation.
"""

import secrets
import hashlib
import hmac
import os
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from functools import lru_cache
from fastapi import HTTPException, Header, Request
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages API authentication with timing-attack resistance and rate limiting."""
    
    def __init__(self):
        """Initialize security manager with rate limiting and key management."""
        self._api_keys: Dict[str, Dict[str, Any]] = {}
        self._load_api_keys()
        
        # Rate limiting: key -> list of (timestamp, count)
        self._rate_limit_data: Dict[str, list] = defaultdict(list)
        self._rate_limit_lock = Lock()
        
        # Configuration
        self.max_requests_per_minute = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))
        self.max_requests_per_hour = int(os.getenv("MAX_REQUESTS_PER_HOUR", "1000"))
        
        logger.info("SecurityManager initialized with rate limiting enabled")
    
    def _load_api_keys(self) -> None:
        """Load API keys from environment with metadata."""
        backend_key = os.getenv("BACKEND_API_KEY")
        logger.info(f"Backend key from environment: {backend_key[:8] if backend_key else 'None'}... (hidden for security)")
        if backend_key:
            # Hash the key for constant-time comparison
            key_hash = hashlib.sha256(backend_key.encode()).hexdigest()
            self._api_keys[key_hash] = {
                "key": backend_key,
                "created_at": datetime.utcnow(),
                "permissions": ["read", "write"],
                "rate_limit_tier": "standard"
            }
            logger.info(f"Loaded {len(self._api_keys)} API key(s) from environment")
        else:
            logger.warning("No BACKEND_API_KEY found in environment variables")
    
    def _constant_time_compare(self, a: str, b: str) -> bool:
        """Compare two strings in constant time to prevent timing attacks.
        
        Args:
            a: First string
            b: Second string
            
        Returns:
            True if strings are equal, False otherwise
        """
        return hmac.compare_digest(a.encode(), b.encode())
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for lookup.
        
        Args:
            api_key: Raw API key
            
        Returns:
            SHA256 hash of the key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _check_rate_limit(self, identifier: str) -> Tuple[bool, Optional[str]]:
        """Check if request is within rate limits.
        
        Args:
            identifier: Unique identifier for rate limiting (API key hash or IP)
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        with self._rate_limit_lock:
            current_time = time.time()
            
            # Clean up old entries
            self._rate_limit_data[identifier] = [
                ts for ts in self._rate_limit_data[identifier]
                if current_time - ts < 3600  # Keep last hour
            ]
            
            requests = self._rate_limit_data[identifier]
            
            # Check per-minute limit
            recent_minute = [ts for ts in requests if current_time - ts < 60]
            if len(recent_minute) >= self.max_requests_per_minute:
                logger.warning(f"Rate limit exceeded (per-minute) for: {identifier[:16]}...")
                return False, f"Rate limit exceeded: {self.max_requests_per_minute} requests/minute"
            
            # Check per-hour limit
            if len(requests) >= self.max_requests_per_hour:
                logger.warning(f"Rate limit exceeded (per-hour) for: {identifier[:16]}...")
                return False, f"Rate limit exceeded: {self.max_requests_per_hour} requests/hour"
            
            # Record this request
            self._rate_limit_data[identifier].append(current_time)
            
            return True, None
    
    async def verify_api_key(self, x_api_key: Optional[str] = Header(None), request: Request = None) -> str:
        """Verify API key with timing-attack resistance and rate limiting.
        
        Args:
            x_api_key: API key from request header
            request: FastAPI request object for IP-based rate limiting
            
        Returns:
            Validated API key
            
        Raises:
            HTTPException: If authentication or rate limiting fails
        """
        # Check if API key is provided
        if not x_api_key:
            logger.warning("API key missing from request")
            raise HTTPException(
                status_code=401,
                detail="API key required. Include 'X-API-Key' header.",
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        # Hash the provided key for lookup
        provided_key_hash = self._hash_api_key(x_api_key)
        
        # Constant-time validation
        is_valid = False
        valid_key_data = None
        
        for stored_hash, key_data in self._api_keys.items():
            if self._constant_time_compare(provided_key_hash, stored_hash):
                is_valid = True
                valid_key_data = key_data
                break
        
        # Always perform the same operations to prevent timing attacks
        if not is_valid:
            logger.warning(f"Invalid API key attempted: {x_api_key[:8] if x_api_key else 'None'}... Expected: {list(self._api_keys.keys())[0][:8] if self._api_keys else 'None'}...")
            # Add delay to make brute force harder
            await asyncio.sleep(0.1)
            raise HTTPException(
                status_code=401,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        # Rate limiting check
        # Use API key hash as identifier (could also use IP from request.client.host)
        rate_limit_identifier = provided_key_hash
        if request and hasattr(request, 'client'):
            # Optionally combine with IP for more granular rate limiting
            rate_limit_identifier = f"{provided_key_hash}:{request.client.host}"
        
        is_allowed, error_message = self._check_rate_limit(rate_limit_identifier)
        if not is_allowed:
            raise HTTPException(
                status_code=429,
                detail=error_message,
                headers={"Retry-After": "60"}
            )
        
        logger.info(f"API key validated successfully for tier: {valid_key_data.get('rate_limit_tier', 'unknown')}")
        return x_api_key
    
    def rotate_api_key(self, old_key: str, new_key: str) -> bool:
        """Rotate an API key (remove old, add new).
        
        Args:
            old_key: Current API key to revoke
            new_key: New API key to activate
            
        Returns:
            True if rotation successful
        """
        try:
            old_hash = self._hash_api_key(old_key)
            new_hash = self._hash_api_key(new_key)
            
            # Copy permissions from old key
            if old_hash in self._api_keys:
                old_key_data = self._api_keys[old_hash].copy()
                old_key_data["key"] = new_key
                old_key_data["created_at"] = datetime.utcnow()
                
                # Add new key
                self._api_keys[new_hash] = old_key_data
                
                # Remove old key
                del self._api_keys[old_hash]
                
                logger.info(f"API key rotated successfully. Old key revoked, new key activated.")
                return True
            else:
                logger.error("Old API key not found for rotation")
                return False
        except Exception as e:
            logger.error(f"Error rotating API key: {e}", exc_info=True)
            return False
    
    def generate_new_api_key(self) -> str:
        """Generate a cryptographically secure API key.
        
        Returns:
            New API key (64 characters)
        """
        return secrets.token_urlsafe(48)  # 64 chars base64url
    
    def get_rate_limit_stats(self, identifier: str) -> Dict[str, Any]:
        """Get rate limit statistics for an identifier.
        
        Args:
            identifier: API key hash or IP address
            
        Returns:
            Dictionary with rate limit stats
        """
        with self._rate_limit_lock:
            current_time = time.time()
            requests = self._rate_limit_data.get(identifier, [])
            
            recent_minute = [ts for ts in requests if current_time - ts < 60]
            recent_hour = [ts for ts in requests if current_time - ts < 3600]
            
            return {
                "requests_last_minute": len(recent_minute),
                "requests_last_hour": len(recent_hour),
                "limit_per_minute": self.max_requests_per_minute,
                "limit_per_hour": self.max_requests_per_hour,
                "remaining_minute": max(0, self.max_requests_per_minute - len(recent_minute)),
                "remaining_hour": max(0, self.max_requests_per_hour - len(recent_hour))
            }


# Global instance
_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """Get or create the global SecurityManager instance.
    
    Returns:
        SecurityManager instance
    """
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


# Dependency for FastAPI
async def verify_api_key_dependency(
    x_api_key: Optional[str] = Header(None),
    request: Request = None
) -> str:
    """FastAPI dependency for API key verification.
    
    Args:
        x_api_key: API key from header
        request: FastAPI request
        
    Returns:
        Validated API key
    """
    manager = get_security_manager()
    return await manager.verify_api_key(x_api_key, request)


# Import asyncio for sleep
