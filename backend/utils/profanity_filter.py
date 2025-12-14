# utils/profanity_filter.py - Profanity and Inappropriate Content Filter
"""
Simple but effective profanity filter to prevent inappropriate content 
from being processed and creating tasks.
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Basic profanity list - can be expanded as needed
PROFANITY_WORDS = [
    # Strong profanity
    r'\bbitch(es)?\b',
    r'\b(shit|shitty|shitter)\b',
    r'\bfuck(er|ing|ed|s)?\b',
    r'\bdamn(ed)?\b',
    r'\bhell\b',
    r'\bastard(s)?\b',
    
    # Mild profanity and inappropriate terms
    r'\bstupid\b',
    r'\bidiot(ic)?\b',
    r'\bmoron(s)?\b',
    r'\bretard(ed)?\b',
    
    # Offensive terms about AI
    r'\bbad ai\b',
    r'\bstupid ai\b',
    r'\bdumb ai\b',
    
    # Other inappropriate content patterns
    r'\bhate you\b',
    r'\bscrew you\b',
]

# Compile the profanity patterns for better performance
PROFANITY_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in PROFANITY_WORDS]

def contains_profanity(text: str) -> bool:
    """Check if text contains profanity or inappropriate content.
    
    Args:
        text: Text to check for profanity
        
    Returns:
        True if profanity is detected, False otherwise
    """
    if not text:
        return False
    
    # Check each pattern
    for pattern in PROFANITY_PATTERNS:
        if pattern.search(text):
            return True
    
    return False

def filter_profanity(text: str, replacement: str = "[REDACTED]") -> str:
    """Filter profanity from text by replacing it with a placeholder.
    
    Args:
        text: Text to filter
        replacement: String to replace profanity with
        
    Returns:
        Filtered text with profanity replaced
    """
    if not text:
        return text
    
    filtered_text = text
    for pattern in PROFANITY_PATTERNS:
        filtered_text = pattern.sub(replacement, filtered_text)
    
    return filtered_text

def validate_content(text: str) -> Tuple[bool, str]:
    """Validate content for appropriateness.
    
    Args:
        text: Text to validate
        
    Returns:
        Tuple of (is_appropriate, error_message)
    """
    if not text:
        return False, "Content cannot be empty"
    
    if contains_profanity(text):
        return False, "Inappropriate content detected"
    
    return True, ""