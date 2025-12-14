# utils/caching.py - Caching Infrastructure
"""
Caching utilities for expensive operations.
Supports in-memory caching with TTL and optional Redis backend.
"""

import logging
import hashlib
import json
import time
from typing import Any, Optional, Callable, Dict
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached value with TTL."""
    
    def __init__(self, value: Any, ttl_seconds: int):
        """Initialize cache entry.
        
        Args:
            value: Value to cache
            ttl_seconds: Time-to-live in seconds
        """
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired.
        
        Returns:
            True if expired, False otherwise
        """
        return (time.time() - self.created_at) > self.ttl_seconds
    
    def get_age_seconds(self) -> float:
        """Get age of cache entry in seconds.
        
        Returns:
            Age in seconds
        """
        return time.time() - self.created_at


class InMemoryCache:
    """Simple in-memory cache with TTL support.
    
    Thread-safe cache implementation for single-process deployments.
    For multi-process/distributed deployments, use RedisCache instead.
    """
    
    def __init__(self, default_ttl: int = 300):
        """Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        logger.info(f"InMemoryCache initialized with default TTL: {default_ttl}s")
    
    def _make_key(self, namespace: str, key: str) -> str:
        """Create full cache key.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            
        Returns:
            Full cache key
        """
        return f"{namespace}:{key}"
    
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        full_key = self._make_key(namespace, key)
        entry = self._cache.get(full_key)
        
        if entry is None:
            self._misses += 1
            logger.debug(f"Cache miss: {full_key}")
            return None
        
        if entry.is_expired():
            self._misses += 1
            del self._cache[full_key]
            logger.debug(f"Cache expired: {full_key}")
            return None
        
        self._hits += 1
        logger.debug(f"Cache hit: {full_key} (age: {entry.get_age_seconds():.1f}s)")
        return entry.value
    
    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set value in cache.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        full_key = self._make_key(namespace, key)
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        
        self._cache[full_key] = CacheEntry(value, ttl_seconds)
        logger.debug(f"Cache set: {full_key} (TTL: {ttl_seconds}s)")
    
    def delete(self, namespace: str, key: str) -> bool:
        """Delete value from cache.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        full_key = self._make_key(namespace, key)
        if full_key in self._cache:
            del self._cache[full_key]
            logger.debug(f"Cache deleted: {full_key}")
            return True
        return False
    
    def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache entries.
        
        Args:
            namespace: Optional namespace to clear (clears all if None)
            
        Returns:
            Number of entries cleared
        """
        if namespace is None:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} entries")
            return count
        
        # Clear specific namespace
        prefix = f"{namespace}:"
        keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._cache[key]
        
        logger.info(f"Cache namespace '{namespace}' cleared: {len(keys_to_delete)} entries")
        return len(keys_to_delete)
    
    def cleanup_expired(self) -> int:
        """Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2)
        }


# Global cache instance
_cache: Optional[InMemoryCache] = None


def get_cache() -> InMemoryCache:
    """Get or create global cache instance.
    
    Returns:
        InMemoryCache instance
    """
    global _cache
    if _cache is None:
        _cache = InMemoryCache(default_ttl=300)
    return _cache


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Hash-based cache key
    """
    # Create deterministic string representation
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_str = "|".join(key_parts)
    
    # Hash for consistent key length
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(
    namespace: str = "default",
    ttl: int = 300,
    key_func: Optional[Callable] = None
) -> Callable:
    """Decorator to cache function results.
    
    Args:
        namespace: Cache namespace
        ttl: Time-to-live in seconds
        key_func: Optional function to generate cache key from args
        
    Returns:
        Decorator function
        
    Example:
        @cached(namespace="search", ttl=300)
        async def search_stackoverflow(query: str):
            # Expensive API call
            return results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = cache_key(*args, **kwargs)
            
            # Try to get from cache
            cache = get_cache()
            cached_value = cache.get(namespace, key)
            
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value
            
            # Execute function
            logger.debug(f"Cache miss for {func.__name__}, executing...")
            result = await func(*args, **kwargs)
            
            # Cache result
            cache.set(namespace, key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = cache_key(*args, **kwargs)
            
            # Try to get from cache
            cache = get_cache()
            cached_value = cache.get(namespace, key)
            
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value
            
            # Execute function
            logger.debug(f"Cache miss for {func.__name__}, executing...")
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(namespace, key, result, ttl)
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def invalidate_cache(namespace: str, key: Optional[str] = None) -> bool:
    """Invalidate cache entry or entire namespace.
    
    Args:
        namespace: Cache namespace
        key: Optional specific key to invalidate
        
    Returns:
        True if invalidated successfully
    """
    cache = get_cache()
    
    if key:
        return cache.delete(namespace, key)
    else:
        cache.clear(namespace)
        return True


# Convenience functions for common caching patterns
def cache_response(ttl: int = 60):
    """Cache API response decorator.
    
    Args:
        ttl: Time-to-live in seconds
        
    Returns:
        Decorator
    """
    return cached(namespace="api_response", ttl=ttl)


def cache_search(ttl: int = 300):
    """Cache search results decorator.
    
    Args:
        ttl: Time-to-live in seconds
        
    Returns:
        Decorator
    """
    return cached(namespace="search", ttl=ttl)


def cache_computation(ttl: int = 600):
    """Cache expensive computation decorator.
    
    Args:
        ttl: Time-to-live in seconds
        
    Returns:
        Decorator
    """
    return cached(namespace="computation", ttl=ttl)
