# utils/logging_sanitizer.py - Sensitive Data Sanitization for Logs
"""
Utility module for sanitizing sensitive information from log messages.
Prevents PII, credentials, and sensitive business data from appearing in logs.
"""

import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LogSanitizer:
    """Sanitizes sensitive data from log messages."""
    
    # Patterns for sensitive data detection
    PATTERNS = {
        # Email addresses
        'email': (
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL_REDACTED]'
        ),
        
        # API keys (32+ alphanumeric characters)
        'api_key': (
            r'\b[A-Za-z0-9_-]{32,}\b',
            '[API_KEY_REDACTED]'
        ),
        
        # Passwords (various patterns)
        'password': (
            r'password["\s:=]+[^\s"]+',
            'password=[REDACTED]'
        ),
        
        # Tokens (JWT pattern)
        'jwt': (
            r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*',
            '[JWT_REDACTED]'
        ),
        
        # Credit card numbers (basic pattern)
        'credit_card': (
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            '[CARD_REDACTED]'
        ),
        
        # Social Security Numbers (US)
        'ssn': (
            r'\b\d{3}-\d{2}-\d{4}\b',
            '[SSN_REDACTED]'
        ),
        
        # IP addresses (optional - may be needed for debugging)
        'ip_address': (
            r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            '[IP_REDACTED]'
        ),
        
        # Authorization headers
        'auth_header': (
            r'(Bearer|Basic)\s+[A-Za-z0-9+/=]+',
            r'\1 [TOKEN_REDACTED]'
        ),
        
        # Database connection strings
        'db_connection': (
            r'(postgres|mysql|mongodb)://[^@]+@',
            r'\1://[USER_REDACTED]@'
        ),
        
        # Private keys
        'private_key': (
            r'-----BEGIN (RSA |)PRIVATE KEY-----[\s\S]*?-----END (RSA |)PRIVATE KEY-----',
            '-----BEGIN PRIVATE KEY-----[REDACTED]-----END PRIVATE KEY-----'
        ),
    }
    
    def __init__(self, enable_ip_redaction: bool = False):
        """Initialize sanitizer.
        
        Args:
            enable_ip_redaction: Whether to redact IP addresses (default: False)
        """
        self.enable_ip_redaction = enable_ip_redaction
        logger.info(f"LogSanitizer initialized (IP redaction: {enable_ip_redaction})")
    
    def sanitize(self, message: str) -> str:
        """Sanitize a log message by removing sensitive data.
        
        Args:
            message: Original log message
            
        Returns:
            Sanitized log message with sensitive data redacted
        """
        if not message:
            return message
        
        sanitized = message
        
        for pattern_name, (pattern, replacement) in self.PATTERNS.items():
            # Skip IP redaction if not enabled
            if pattern_name == 'ip_address' and not self.enable_ip_redaction:
                continue
            
            try:
                sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
            except Exception as e:
                logger.error(f"Error applying {pattern_name} pattern: {e}")
        
        return sanitized
    
    def sanitize_dict(self, data: Dict[str, Any], keys_to_redact: List[str] = None) -> Dict[str, Any]:
        """Sanitize dictionary values (for structured logging).
        
        Args:
            data: Dictionary to sanitize
            keys_to_redact: List of keys whose values should be fully redacted
            
        Returns:
            Sanitized dictionary
        """
        if keys_to_redact is None:
            keys_to_redact = [
                'password', 'api_key', 'token', 'secret', 'apikey',
                'auth', 'authorization', 'x-api-key', 'private_key'
            ]
        
        sanitized = {}
        for key, value in data.items():
            # Check if key should be fully redacted
            if any(redact_key.lower() in key.lower() for redact_key in keys_to_redact):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, str):
                sanitized[key] = self.sanitize(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value, keys_to_redact)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def sanitize_query(self, query: str, max_length: int = 200) -> str:
        """Sanitize and truncate a database query for logging.
        
        Args:
            query: SQL or search query
            max_length: Maximum length to include in logs
            
        Returns:
            Sanitized and truncated query
        """
        # First sanitize for sensitive data
        sanitized = self.sanitize(query)
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + '...[TRUNCATED]'
        
        return sanitized


# Global sanitizer instance
_sanitizer: Optional[LogSanitizer] = None


def get_sanitizer(enable_ip_redaction: bool = False) -> LogSanitizer:
    """Get or create the global LogSanitizer instance.
    
    Args:
        enable_ip_redaction: Whether to redact IP addresses
        
    Returns:
        LogSanitizer instance
    """
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = LogSanitizer(enable_ip_redaction=enable_ip_redaction)
    return _sanitizer


def sanitize_log_message(message: str) -> str:
    """Convenience function to sanitize a log message.
    
    Args:
        message: Original log message
        
    Returns:
        Sanitized log message
    """
    sanitizer = get_sanitizer()
    return sanitizer.sanitize(message)


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to sanitize structured log data.
    
    Args:
        data: Dictionary to sanitize
        
    Returns:
        Sanitized dictionary
    """
    sanitizer = get_sanitizer()
    return sanitizer.sanitize_dict(data)


# Custom logging handler that auto-sanitizes
class SanitizingHandler(logging.Handler):
    """Logging handler that automatically sanitizes log messages."""
    
    def __init__(self, base_handler: logging.Handler, sanitizer: LogSanitizer = None):
        """Initialize sanitizing handler.
        
        Args:
            base_handler: Underlying handler to forward sanitized logs to
            sanitizer: LogSanitizer instance (creates new one if None)
        """
        super().__init__()
        self.base_handler = base_handler
        self.sanitizer = sanitizer or get_sanitizer()
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record after sanitizing the message.
        
        Args:
            record: Log record to emit
        """
        try:
            # Sanitize the message
            record.msg = self.sanitizer.sanitize(str(record.msg))
            
            # Sanitize args if present
            if record.args:
                record.args = tuple(
                    self.sanitizer.sanitize(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
            
            # Forward to base handler
            self.base_handler.emit(record)
        except Exception as e:
            self.handleError(record)
