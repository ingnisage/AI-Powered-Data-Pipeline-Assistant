# backend/utils/query_processing.py - Query Processing Utilities
"""
Utilities for processing and optimizing search queries, especially for error messages.
"""

import re
from typing import Optional

def preprocess_search_query(query: str) -> str:
    """Preprocess search query to make it more effective for searching.
    
    For error messages, this extracts the essential parts and removes noise.
    
    Args:
        query: Raw search query
        
    Returns:
        Processed query optimized for search
    """
    if not query or not query.strip():
        return ""
    
    # If it looks like an error message, extract key parts
    if _looks_like_error_message(query):
        return _extract_error_keywords(query)
    
    # For regular queries, clean them up
    return _clean_regular_query(query)

def _looks_like_error_message(text: str) -> bool:
    """Check if text looks like an error message."""
    error_indicators = [
        r'\.utils\.',  # Java/Python style error
        r'Exception:',
        r'Error:',
        r'Traceback',
        r'Caused by:',
        r'at [a-zA-Z0-9_.]+\(',  # Stack trace lines
        r'\[.*\]',  # Error codes in brackets
        r'cannot be found',
        r'not found',
        r'does not exist',
    ]
    
    text_lower = text.lower()
    return any(re.search(indicator, text_lower) for indicator in error_indicators)

def _extract_error_keywords(text: str) -> str:
    """Extract key keywords from error message for better search results."""
    # For error messages, we want to extract the most relevant parts
    # Strategy: Extract exception type and create generalized search terms
    
    # Clean up the text - remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', text).strip()
    
    # Extract exception type if present
    exception_match = re.search(r'([a-zA-Z0-9_.]+Exception)', cleaned)
    exception_type = exception_match.group(1) if exception_match else None
    
    # Extract error code if present (text in brackets)
    error_code_match = re.search(r'\[([^\]]+)\]', cleaned)
    error_code = error_code_match.group(1) if error_code_match else None
    
    # For database errors, extract table/view names
    table_match = re.search(r'[`"\']([a-zA-Z0-9_]+\.?[a-zA-Z0-9_]*)[`"\']', cleaned)
    table_name = table_match.group(1) if table_match else None
    
    # Also look for table names without quotes
    table_match_no_quotes = re.search(r'\b([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\b', cleaned)
    if not table_name and table_match_no_quotes:
        table_name = table_match_no_quotes.group(1)
    
    # Build multiple search queries and return the most promising one
    candidates = []
    
    # Candidate 1: Generalized terms (most likely to succeed)
    table_related = 'table' in cleaned.lower() or 'view' in cleaned.lower()
    not_found_related = 'not found' in cleaned.lower() or 'cannot be found' in cleaned.lower()
    
    if table_related and not_found_related:
        if exception_type and 'spark' in exception_type.lower():
            candidates.append("pyspark table not found")
        else:
            candidates.append("sql table not found")
    
    # Candidate 2: Exception type + error code
    if exception_type and error_code:
        candidates.append(f"{exception_type} {error_code}")
    
    # Candidate 3: Exception type + table name
    if exception_type and table_name:
        candidates.append(f"{exception_type} {table_name}")
    
    # Candidate 4: Just the exception type
    if exception_type:
        candidates.append(exception_type)
    
    # Candidate 5: Error code
    if error_code:
        candidates.append(error_code)
    
    # Candidate 6: Table name
    if table_name:
        candidates.append(table_name)
    
    # Return the first candidate, or a cleaned version of the original if no candidates
    if candidates:
        return candidates[0][:100].strip()
    else:
        # Fallback: clean up and truncate the original
        result = re.sub(r'\s+', ' ', cleaned).strip()
        return result[:100].strip()

def _clean_regular_query(query: str) -> str:
    """Clean up regular search queries."""
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', query.strip())
    
    # Limit length
    if len(cleaned) > 200:
        cleaned = cleaned[:200].strip()
    
    return cleaned