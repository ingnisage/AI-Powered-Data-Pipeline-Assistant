# models/chat.py - Chat Message Models with Validation
"""
Pydantic models for chat messages with proper validation and sanitization.
Includes size limits and content validation to prevent injection attacks.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
import html
import re


class ChatMessage(BaseModel):
    """Chat message with validation and size limits."""
    
    message: str = Field(
        ..., 
        max_length=10000,
        description="User message content",
        example="Hello, how can I optimize my data pipeline?"
    )
    
    system_prompt: str = Field(
        default="data_engineer",
        max_length=50,
        description="System prompt to use",
        example="data_engineer"
    )
    
    use_tools: bool = Field(
        default=False,
        description="Whether to use tools in response"
    )
    
    session_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Session identifier",
        example="sess_abc123"
    )
    
    user_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User identifier",
        example="user_xyz789"
    )
    
    search_source: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Search source restriction",
        example="stackoverflow"
    )
    
    @validator('message')
    def message_not_empty(cls, v):
        """Ensure message is not empty or only whitespace."""
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()
    
    @validator('message')
    def sanitize_message(cls, v):
        """Sanitize message to prevent injection attacks."""
        if not v:
            return v
        
        # Remove null bytes
        sanitized = v.replace('\x00', '')
        
        # Limit consecutive newlines (prevent log injection)
        sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)
        
        return sanitized
    
    @validator('system_prompt')
    def validate_system_prompt(cls, v):
        """Validate system prompt value."""
        if not v:
            return "general"
        
        # Allow only alphanumeric, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid system prompt format')
        
        return v
    
    @validator('session_id')
    def validate_session_id(cls, v):
        """Validate session ID format."""
        if v is None:
            return v
        
        # Remove any dangerous characters
        sanitized = re.sub(r'[<>"\';&]', '_', v)
        return sanitized[:100]  # Enforce max length
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user ID format."""
        if v is None:
            return v
        
        # Remove any dangerous characters
        sanitized = re.sub(r'[<>"\';&]', '_', v)
        return sanitized[:100]  # Enforce max length


class NewTask(BaseModel):
    """Model for creating new tasks."""
    
    name: str = Field(
        ..., 
        max_length=200,
        description="Task name",
        example="Optimize database queries"
    )
    
    @validator('name')
    def task_name_not_empty(cls, v):
        """Ensure task name is not empty."""
        if not v or not v.strip():
            raise ValueError('Task name cannot be empty')
        return v.strip()
    
    @validator('name')
    def sanitize_task_name(cls, v):
        """Sanitize task name."""
        if not v:
            return v
        
        # Remove dangerous characters
        forbidden_chars = ['<', '>', '{', '}', '\x00']
        for char in forbidden_chars:
            if char in v:
                raise ValueError('Task name contains invalid characters')
        
        # HTML escape for safety
        return html.escape(v.strip())


class TaskUpdate(BaseModel):
    """Model for updating existing tasks."""
    
    name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Updated task name"
    )
    
    status: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Task status"
    )
    
    progress: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Task progress percentage"
    )
    
    priority: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Task priority"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Task description"
    )
    
    @validator('name')
    def validate_name(cls, v):
        """Validate task name."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Task name cannot be empty')
        
        # Check for dangerous characters
        forbidden_chars = ['<', '>', '{', '}', '\x00']
        for char in forbidden_chars:
            if char in v:
                raise ValueError('Task name contains invalid characters')
        
        return html.escape(v.strip())
    
    @validator('status')
    def validate_status(cls, v):
        """Validate task status."""
        if v is None:
            return v
        
        valid_statuses = [
            "Pending", "In Progress", 
            "Completed", "Failed"
        ]
        
        if v not in valid_statuses:
            raise ValueError(f'Invalid status. Must be one of: {valid_statuses}')
        
        return v


class SearchRequest(BaseModel):
    """Model for search requests."""
    
    source: str = Field(
        ..., 
        max_length=50,
        description="Search source",
        example="stackoverflow"
    )
    
    query: str = Field(
        ..., 
        max_length=500,
        min_length=1,
        description="Search query",
        example="how to optimize SQL queries"
    )
    
    max_results: Optional[int] = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum number of results"
    )
    
    @validator('query')
    def validate_query(cls, v):
        """Validate search query."""
        if not v or not v.strip():
            raise ValueError('Search query cannot be empty')
        
        # Check for null bytes
        if '\x00' in v:
            raise ValueError('Search query contains invalid characters')
        
        # Limit consecutive spaces
        v = re.sub(r'\s+', ' ', v.strip())
        
        return v
    
    @validator('source')
    def validate_source(cls, v):
        """Validate search source."""
        valid_sources = ["github", "stackoverflow", "official_doc", "spark_docs", "all"]
        
        if v not in valid_sources:
            raise ValueError(f'Invalid source. Must be one of: {valid_sources}')
        
        return v
