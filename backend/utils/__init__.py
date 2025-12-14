# utils/__init__.py
"""Utility modules for the application."""

from .logging_sanitizer import sanitize_log_message, sanitize_log_data, LogSanitizer, get_sanitizer
from .sql_safety import validate_sql_query, safe_execute_query, SQLQueryValidator, SafeQueryExecutor
from .caching import (
    InMemoryCache,
    get_cache,
    cache_key,
    cached,
    invalidate_cache,
    cache_response,
    cache_search,
    cache_computation,
)
from .sanitization import (
    InputSanitizer,
    SanitizationLevel,
    sanitize_for_display,
    sanitize_for_log,
    sanitize_html,
    ContentValidator,
)
from .logging_helpers import save_log, log_and_publish, save_chat_message
from .profanity_filter import contains_profanity, filter_profanity, validate_content

__all__ = [
    # Logging sanitization
    'sanitize_log_message',
    'sanitize_log_data',
    'LogSanitizer',
    'get_sanitizer',
    
    # SQL safety
    'validate_sql_query',
    'safe_execute_query',
    'SQLQueryValidator',
    'SafeQueryExecutor',
    
    # Caching
    'InMemoryCache',
    'get_cache',
    'cache_key',
    'cached',
    'invalidate_cache',
    'cache_response',
    'cache_search',
    'cache_computation',
    
    # Sanitization
    'InputSanitizer',
    'SanitizationLevel',
    'sanitize_for_display',
    'sanitize_for_log',
    'sanitize_html',
    'ContentValidator',
    
    # Logging helpers
    'save_log',
    'log_and_publish',
    'save_chat_message',
    
    # Profanity filter
    'contains_profanity',
    'filter_profanity',
    'validate_content',
]