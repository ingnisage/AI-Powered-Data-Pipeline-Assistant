# models/logging.py - Structured Logging Models
"""
Pydantic models for consistent logging throughout the application.
Ensures standardized function signatures and structured data.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import html
import re


class LogLevel(str, Enum):
    """Standardized log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogSource(str, Enum):
    """Common log sources across the application."""
    SYSTEM = "system"
    CHAT = "chat"
    SEARCH = "search"
    TOOLS = "tools"
    API = "api"
    DATABASE = "database"
    PIPELINE = "pipeline"
    MONITORING = "monitoring"


class LogEntry(BaseModel):
    """Base model for all log entries.
    
    Provides consistent structure for logging across the application.
    """
    level: LogLevel
    message: str
    source: LogSource = LogSource.SYSTEM
    component: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    duration_ms: Optional[int] = Field(None, ge=0, description="Operation duration in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    time: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('message')
    def message_not_empty(cls, v):
        """Ensure message is not empty."""
        if not v or not v.strip():
            raise ValueError("Log message cannot be empty")
        return v.strip()
    
    @validator('message')
    def sanitize_message(cls, v):
        """Sanitize log message to prevent injection attacks."""
        if not v:
            return v
        
        # HTML escape to prevent XSS in log viewers
        sanitized = html.escape(v[:1000])  # Limit length for display
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Remove newlines to prevent log injection
        sanitized = sanitized.replace('\n', ' ').replace('\r', ' ')
        
        return sanitized
    
    @validator('metadata')
    def sanitize_metadata(cls, v):
        """Ensure metadata is JSON-serializable and sanitized."""
        # Remove any non-serializable values
        sanitized = {}
        for k, val in v.items():
            # Convert key to string
            key = str(k)[:100]  # Limit key length
            
            # Sanitize value
            if isinstance(val, str):
                # Limit string values and sanitize
                sanitized[key] = html.escape(val[:500]).replace('\x00', '').replace('\n', ' ')
            elif isinstance(val, (int, float, bool, type(None))):
                sanitized[key] = val
            else:
                # Convert other types to string
                sanitized[key] = html.escape(str(val)[:500]).replace('\x00', '').replace('\n', ' ')
        
        return sanitized
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage.
        
        Returns:
            Dictionary representation suitable for Supabase insertion
        """
        return {
            "level": self.level.value,
            "message": self.message,
            "source": self.source.value,
            "component": self.component,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "time": self.time.isoformat() if self.time else None
        }


class PublishableLogEntry(LogEntry):
    """Log entry that can be published to PubNub.
    
    Extends LogEntry with channel information for real-time publishing.
    """
    publish_channel: Optional[str] = None
    
    @validator('message')
    def sanitize_message_for_publishing(cls, v):
        """Sanitize message specifically for real-time publishing."""
        if not v:
            return v
        
        # HTML escape for safe display in UI
        sanitized = html.escape(v[:1000])  # Limit length
        
        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        
        return sanitized
    
    def to_publish_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for PubNub publishing.
        
        Returns:
            Dictionary with minimal fields for real-time updates
        """
        return {
            "time": self.time.strftime("%H:%M:%S") if self.time else datetime.utcnow().strftime("%H:%M:%S"),
            "level": self.level.value,
            "message": self.message,
            "source": self.source.value,
            "component": self.component
        }


class ChatMessageRole(str, Enum):
    """Standardized chat message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ChatMessageEntry(BaseModel):
    """Structured model for chat message persistence.
    
    Ensures consistent chat history storage with all relevant context.
    """
    role: ChatMessageRole
    content: str
    system_prompt: str = "data_engineer"
    session_id: str = "default_session"
    user_id: Optional[str] = None
    tools_used: List[str] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    rag_sources: List[Dict[str, Any]] = Field(default_factory=list)
    tokens_used: Optional[int] = Field(None, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('content')
    def content_not_empty(cls, v):
        """Ensure content is not empty."""
        if not v or not v.strip():
            raise ValueError("Chat message content cannot be empty")
        return v.strip()
    
    @validator('content')
    def sanitize_content(cls, v):
        """Sanitize chat content."""
        if not v:
            return v
        
        # Limit length
        content = v[:5000]  # Reasonable limit for chat messages
        
        # Remove null bytes
        content = content.replace('\x00', '')
        
        return content
    
    @validator('session_id')
    def session_id_not_empty(cls, v):
        """Ensure session_id is not empty."""
        if not v or not v.strip():
            return "default_session"
        return v.strip()[:100]  # Limit length
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage.
        
        Returns:
            Dictionary representation suitable for Supabase insertion
        """
        return {
            "role": self.role.value,
            "content": self.content,
            "system_prompt": self.system_prompt,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "tools_used": self.tools_used,
            "tool_results": self.tool_results,
            "rag_sources": self.rag_sources,
            "tokens_used": self.tokens_used,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# Convenience builders for common log scenarios
class LogBuilder:
    """Builder pattern for creating log entries with sensible defaults."""
    
    @staticmethod
    def info(
        message: str,
        source: LogSource = LogSource.SYSTEM,
        component: Optional[str] = None,
        **kwargs
    ) -> LogEntry:
        """Create an INFO level log entry."""
        return LogEntry(
            level=LogLevel.INFO,
            message=message,
            source=source,
            component=component,
            **kwargs
        )
    
    @staticmethod
    def warning(
        message: str,
        source: LogSource = LogSource.SYSTEM,
        component: Optional[str] = None,
        **kwargs
    ) -> LogEntry:
        """Create a WARNING level log entry."""
        return LogEntry(
            level=LogLevel.WARNING,
            message=message,
            source=source,
            component=component,
            **kwargs
        )
    
    @staticmethod
    def error(
        message: str,
        source: LogSource = LogSource.SYSTEM,
        component: Optional[str] = None,
        **kwargs
    ) -> LogEntry:
        """Create an ERROR level log entry."""
        return LogEntry(
            level=LogLevel.ERROR,
            message=message,
            source=source,
            component=component,
            **kwargs
        )
    
    @staticmethod
    def debug(
        message: str,
        source: LogSource = LogSource.SYSTEM,
        component: Optional[str] = None,
        **kwargs
    ) -> LogEntry:
        """Create a DEBUG level log entry."""
        return LogEntry(
            level=LogLevel.DEBUG,
            message=message,
            source=source,
            component=component,
            **kwargs
        )
    
    @staticmethod
    def publishable(
        message: str,
        level: LogLevel,
        source: LogSource,
        channel: str,
        component: Optional[str] = None,
        **kwargs
    ) -> PublishableLogEntry:
        """Create a publishable log entry for PubNub."""
        return PublishableLogEntry(
            level=level,
            message=message,
            source=source,
            component=component,
            publish_channel=channel,
            **kwargs
        )


class ChatMessageBuilder:
    """Builder pattern for creating chat message entries."""
    
    @staticmethod
    def user_message(
        content: str,
        session_id: str = "default_session",
        user_id: Optional[str] = None,
        system_prompt: str = "data_engineer",
        **kwargs
    ) -> ChatMessageEntry:
        """Create a user chat message entry."""
        return ChatMessageEntry(
            role=ChatMessageRole.USER,
            content=content,
            session_id=session_id,
            user_id=user_id,
            system_prompt=system_prompt,
            **kwargs
        )
    
    @staticmethod
    def assistant_message(
        content: str,
        session_id: str = "default_session",
        user_id: Optional[str] = None,
        system_prompt: str = "data_engineer",
        tools_used: Optional[List[str]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        tokens_used: Optional[int] = None,
        **kwargs
    ) -> ChatMessageEntry:
        """Create an assistant chat message entry."""
        return ChatMessageEntry(
            role=ChatMessageRole.ASSISTANT,
            content=content,
            session_id=session_id,
            user_id=user_id,
            system_prompt=system_prompt,
            tools_used=tools_used or [],
            tool_results=tool_results or [],
            tokens_used=tokens_used,
            **kwargs
        )
    
    @staticmethod
    def tool_message(
        content: str,
        session_id: str = "default_session",
        tool_name: Optional[str] = None,
        **kwargs
    ) -> ChatMessageEntry:
        """Create a tool response message entry."""
        metadata = kwargs.get('metadata', {})
        if tool_name:
            metadata['tool_name'] = tool_name
        kwargs['metadata'] = metadata
        
        return ChatMessageEntry(
            role=ChatMessageRole.TOOL,
            content=content,
            session_id=session_id,
            **kwargs
        )