# utils/sanitization.py - Input Sanitization and Validation
"""
Security utilities for sanitizing user input to prevent injection attacks.
Provides HTML escaping, length limits, and content validation.
"""

import html
import re
import logging
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class SanitizationLevel(str, Enum):
    """Sanitization strictness levels."""
    PERMISSIVE = "permissive"  # Basic HTML escape only
    STRICT = "strict"  # Strip all HTML and special chars
    DISPLAY = "display"  # Safe for display in UI


class InputSanitizer:
    """Comprehensive input sanitization for security."""
    
    # Dangerous HTML tags that should always be removed
    DANGEROUS_TAGS = [
        'script', 'iframe', 'object', 'embed', 'applet',
        'link', 'style', 'meta', 'base', 'form'
    ]
    
    # Dangerous attributes
    DANGEROUS_ATTRIBUTES = [
        'onclick', 'onload', 'onerror', 'onmouseover',
        'javascript:', 'vbscript:', 'data:'
    ]
    
    @staticmethod
    def sanitize_for_display(
        text: str,
        max_length: int = 1000,
        escape_html: bool = True
    ) -> str:
        """Sanitize text for safe display in UI.
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            escape_html: Whether to escape HTML entities
            
        Returns:
            Sanitized text safe for display
            
        Example:
            >>> sanitize_for_display("<script>alert('xss')</script>Hello")
            "&lt;script&gt;alert('xss')&lt;/script&gt;Hello"
        """
        if not text:
            return ""
        
        # Truncate to max length
        sanitized = text[:max_length]
        
        # Escape HTML entities
        if escape_html:
            sanitized = html.escape(sanitized)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        logger.debug(f"Sanitized text for display (length: {len(sanitized)})")
        return sanitized
    
    @staticmethod
    def sanitize_for_log(
        text: str,
        max_length: int = 500,
        redact_patterns: Optional[List[str]] = None
    ) -> str:
        """Sanitize text for logging (prevents log injection).
        
        Args:
            text: Input text to sanitize
            max_length: Maximum length for log entry
            redact_patterns: Optional regex patterns to redact
            
        Returns:
            Sanitized text safe for logging
            
        Example:
            >>> sanitize_for_log("User\ninjected\nnewlines")
            "User injected newlines"
        """
        if not text:
            return ""
        
        # Truncate
        sanitized = text[:max_length]
        
        # HTML escape
        sanitized = html.escape(sanitized)
        
        # Remove newlines (prevents log injection)
        sanitized = sanitized.replace('\n', ' ').replace('\r', ' ')
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Redact sensitive patterns if specified
        if redact_patterns:
            for pattern in redact_patterns:
                sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @staticmethod
    def sanitize_html(text: str, allowed_tags: Optional[List[str]] = None) -> str:
        """Strip dangerous HTML while optionally preserving safe tags.
        
        Args:
            text: Input HTML text
            allowed_tags: Optional list of allowed HTML tags
            
        Returns:
            Sanitized HTML
            
        Note:
            If allowed_tags is None, all HTML is escaped.
        """
        if not text:
            return ""
        
        # If no allowed tags, escape everything
        if allowed_tags is None:
            return html.escape(text)
        
        # Remove dangerous tags
        sanitized = text
        for tag in InputSanitizer.DANGEROUS_TAGS:
            # Remove opening and closing tags
            pattern = f'<{tag}[^>]*>.*?</{tag}>|<{tag}[^>]*/?>'
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove dangerous attributes
        for attr in InputSanitizer.DANGEROUS_ATTRIBUTES:
            pattern = f'{attr}\\s*=\\s*["\'][^"\']*["\']'
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Remove non-allowed tags
        if allowed_tags:
            # Build pattern for non-allowed tags
            allowed_set = set(tag.lower() for tag in allowed_tags)
            
            def replace_tag(match):
                tag_name = match.group(1).lower()
                if tag_name in allowed_set:
                    return match.group(0)  # Keep allowed tag
                return ''  # Remove non-allowed tag
            
            pattern = r'<(/?)(\w+)([^>]*)>'
            sanitized = re.sub(pattern, replace_tag, sanitized)
        
        return sanitized
    
    @staticmethod
    def sanitize_sql_identifier(identifier: str) -> str:
        """Sanitize SQL identifier (table/column name).
        
        Args:
            identifier: SQL identifier to sanitize
            
        Returns:
            Sanitized identifier
            
        Raises:
            ValueError: If identifier contains invalid characters
        """
        # Only allow alphanumeric and underscore
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            raise ValueError(f"Invalid SQL identifier: {identifier}")
        
        # Escape with quotes for safety
        return f'"{identifier}"'
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 255) -> str:
        """Sanitize filename to prevent directory traversal.
        
        Args:
            filename: Original filename
            max_length: Maximum filename length
            
        Returns:
            Safe filename
            
        Example:
            >>> sanitize_filename("../../../etc/passwd")
            "etc_passwd"
        """
        if not filename:
            return "untitled"
        
        # Remove directory traversal attempts
        sanitized = filename.replace('..', '').replace('/', '_').replace('\\', '_')
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Only allow safe characters
        sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', sanitized)
        
        # Truncate to max length
        sanitized = sanitized[:max_length]
        
        # Ensure it's not empty
        if not sanitized:
            sanitized = "untitled"
        
        return sanitized
    
    @staticmethod
    def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> bool:
        """Validate URL to prevent SSRF attacks.
        
        Args:
            url: URL to validate
            allowed_schemes: List of allowed URL schemes (default: http, https)
            
        Returns:
            True if URL is safe, False otherwise
        """
        if not url:
            return False
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        # Check scheme
        url_lower = url.lower()
        if not any(url_lower.startswith(f'{scheme}://') for scheme in allowed_schemes):
            logger.warning(f"Invalid URL scheme: {url}")
            return False
        
        # Prevent localhost/internal IP access
        dangerous_hosts = [
            'localhost', '127.0.0.1', '0.0.0.0',
            '169.254.', '10.', '172.16.', '192.168.'
        ]
        
        for host in dangerous_hosts:
            if host in url_lower:
                logger.warning(f"Blocked access to internal host: {url}")
                return False
        
        return True


# Convenience functions
def sanitize_for_display(text: str, max_length: int = 1000) -> str:
    """Sanitize text for display in UI.
    
    Args:
        text: Input text
        max_length: Maximum length
        
    Returns:
        Sanitized text
    """
    return InputSanitizer.sanitize_for_display(text, max_length)


def sanitize_for_log(text: str, max_length: int = 500) -> str:
    """Sanitize text for logging.
    
    Args:
        text: Input text
        max_length: Maximum length
        
    Returns:
        Sanitized text
    """
    return InputSanitizer.sanitize_for_log(text, max_length)


def sanitize_html(text: str, allowed_tags: Optional[List[str]] = None) -> str:
    """Sanitize HTML content.
    
    Args:
        text: HTML text
        allowed_tags: Optional allowed tags
        
    Returns:
        Sanitized HTML
    """
    return InputSanitizer.sanitize_html(text, allowed_tags)


# Content validators for common use cases
class ContentValidator:
    """Validators for common content types."""
    
    @staticmethod
    def validate_message_length(message: str, max_length: int = 10000) -> tuple:
        """Validate message length.
        
        Args:
            message: Message to validate
            max_length: Maximum allowed length
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not message:
            return False, "Message cannot be empty"
        
        if not message.strip():
            return False, "Message cannot be only whitespace"
        
        if len(message) > max_length:
            return False, f"Message too long ({len(message)} chars, max {max_length})"
        
        return True, ""
    
    @staticmethod
    def validate_task_name(name: str, max_length: int = 200) -> tuple:
        """Validate task name.
        
        Args:
            name: Task name
            max_length: Maximum length
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name or not name.strip():
            return False, "Task name cannot be empty"
        
        if len(name) > max_length:
            return False, f"Task name too long (max {max_length} chars)"
        
        # Check for dangerous characters
        forbidden_chars = ['<', '>', '{', '}', '\x00']
        if any(char in name for char in forbidden_chars):
            return False, "Task name contains invalid characters"
        
        return True, ""
    
    @staticmethod
    def validate_search_query(query: str, max_length: int = 500) -> tuple:
        """Validate search query.
        
        Args:
            query: Search query
            max_length: Maximum length
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, "Search query cannot be empty"
        
        # Import config to use consistent minimum length
        from backend.services.config import config
        if len(query) < config.MIN_SEARCH_QUERY_LENGTH:
            return False, f"Search query too short (minimum {config.MIN_SEARCH_QUERY_LENGTH} chars)"
        
        if len(query) > max_length:
            return False, f"Search query too long (max {max_length} chars)"
        
        # Check for null bytes
        if '\x00' in query:
            return False, "Search query contains invalid characters"
        
        return True, ""
