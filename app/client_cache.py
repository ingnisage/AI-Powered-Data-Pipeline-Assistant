# app/client_cache.py - Client-side caching for Streamlit application
"""
Frontend caching mechanism to reduce API calls and improve responsiveness.
"""

from datetime import datetime, timedelta
import json
from typing import Any, Optional
import streamlit as st
import logging
import os

logger = logging.getLogger(__name__)

# Check if running on Render
IS_RENDER = os.getenv('RENDER', '').lower() == 'true'

# Set cache TTL based on environment
DEFAULT_TASKS_TTL_MINUTES = 1 if IS_RENDER else 2  # Shorter TTL on Render
DEFAULT_CHAT_TTL_MINUTES = 2 if IS_RENDER else 5   # Shorter TTL on Render


class ClientCache:
    """Frontend cache mechanism to reduce API calls."""
    
    def __init__(self, ttl_minutes: int = 5):
        """
        Initialize client cache.
        
        Args:
            ttl_minutes: Time-to-live in minutes for cached items
        """
        # Use environment-specific TTL if not explicitly set
        if ttl_minutes == 5:  # Default value
            ttl_minutes = DEFAULT_CHAT_TTL_MINUTES
        
        self.ttl = timedelta(minutes=ttl_minutes)
        # Initialize cache in session state if not exists
        if "client_cache" not in st.session_state:
            st.session_state.client_cache = {}
        if "client_cache_timestamps" not in st.session_state:
            st.session_state.client_cache_timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached data.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        try:
            if key in st.session_state.client_cache:
                timestamp = st.session_state.client_cache_timestamps.get(key)
                if timestamp and datetime.now() - timestamp < self.ttl:
                    logger.debug(f"Cache hit for key: {key}")
                    return st.session_state.client_cache[key]
                else:
                    # Expired - remove from cache
                    logger.debug(f"Cache expired for key: {key}")
                    self.clear(key)
            else:
                logger.debug(f"Cache miss for key: {key}")
            return None
        except Exception as e:
            logger.error(f"Error getting cache data for key {key}: {e}")
            return None
    
    def set(self, key: str, data: Any):
        """
        Set cache data.
        
        Args:
            key: Cache key
            data: Data to cache
        """
        try:
            st.session_state.client_cache[key] = data
            st.session_state.client_cache_timestamps[key] = datetime.now()
            logger.debug(f"Cache set for key: {key}")
        except Exception as e:
            logger.error(f"Error setting cache data for key {key}: {e}")
    
    def clear(self, key: str = None):
        """
        Clear cache.
        
        Args:
            key: Specific key to clear, or None to clear all
        """
        try:
            if key:
                st.session_state.client_cache.pop(key, None)
                st.session_state.client_cache_timestamps.pop(key, None)
                logger.debug(f"Cache cleared for key: {key}")
            else:
                st.session_state.client_cache.clear()
                st.session_state.client_cache_timestamps.clear()
                logger.debug("All cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            total_items = len(st.session_state.client_cache)
            expired_items = 0
            
            # Count expired items
            current_time = datetime.now()
            for key, timestamp in st.session_state.client_cache_timestamps.items():
                if current_time - timestamp >= self.ttl:
                    expired_items += 1
            
            return {
                "total_items": total_items,
                "expired_items": expired_items,
                "active_items": total_items - expired_items
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"total_items": 0, "expired_items": 0, "active_items": 0}


def get_cached_tasks(user_id: str = "default") -> Optional[list]:
    """
    Get tasks with caching.
    
    Args:
        user_id: User identifier for cache key
        
    Returns:
        List of tasks or None if not cached
    """
    try:
        cache = ClientCache(ttl_minutes=DEFAULT_TASKS_TTL_MINUTES)  # Shorter TTL for tasks
        cache_key = f"tasks_{user_id}"
        return cache.get(cache_key)
    except Exception as e:
        logger.error(f"Error getting cached tasks: {e}")
        return None


def cache_tasks(tasks: list, user_id: str = "default"):
    """
    Cache tasks.
    
    Args:
        tasks: List of tasks to cache
        user_id: User identifier for cache key
    """
    try:
        cache = ClientCache(ttl_minutes=DEFAULT_TASKS_TTL_MINUTES)  # Shorter TTL for tasks
        cache_key = f"tasks_{user_id}"
        cache.set(cache_key, tasks)
        logger.info(f"Cached {len(tasks)} tasks for user {user_id}")
    except Exception as e:
        logger.error(f"Error caching tasks: {e}")


def get_cached_chat_history(user_id: str = "default") -> Optional[list]:
    """
    Get chat history with caching.
    
    Args:
        user_id: User identifier for cache key
        
    Returns:
        List of chat messages or None if not cached
    """
    try:
        cache = ClientCache(ttl_minutes=DEFAULT_CHAT_TTL_MINUTES)  # Longer TTL for chat history
        cache_key = f"chat_history_{user_id}"
        return cache.get(cache_key)
    except Exception as e:
        logger.error(f"Error getting cached chat history: {e}")
        return None


def cache_chat_history(messages: list, user_id: str = "default"):
    """
    Cache chat history.
    
    Args:
        messages: List of chat messages to cache
        user_id: User identifier for cache key
    """
    try:
        cache = ClientCache(ttl_minutes=DEFAULT_CHAT_TTL_MINUTES)  # Longer TTL for chat history
        cache_key = f"chat_history_{user_id}"
        cache.set(cache_key, messages)
        logger.info(f"Cached {len(messages)} chat messages for user {user_id}")
    except Exception as e:
        logger.error(f"Error caching chat history: {e}")


def clear_cache(user_id: str = "default", cache_type: str = "all"):
    """
    Clear specific or all cache.
    
    Args:
        user_id: User identifier for cache key
        cache_type: Type of cache to clear ("tasks", "chat", "all")
    """
    try:
        cache = ClientCache()
        if cache_type == "tasks":
            cache.clear(f"tasks_{user_id}")
        elif cache_type == "chat":
            cache.clear(f"chat_history_{user_id}")
        else:
            cache.clear()  # Clear all cache
        logger.info(f"Cleared {cache_type} cache for user {user_id}")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")