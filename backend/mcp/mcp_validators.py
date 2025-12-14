# backend/validators/mcp_validators.py - MCP Tool Input Validators
"""
Pydantic models for validating MCP tool arguments to prevent errors and ensure security.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class SearchKnowledgeArgs(BaseModel):
    """Validated arguments for search_knowledge tool"""
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=500,
        description="Search query string",
        example="How to optimize data pipelines"
    )
    source: str = Field(
        default="all",
        description="Source to search in",
        example="stackoverflow"
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of results to return",
        example=5
    )
    
    @validator('source')
    def validate_source(cls, v):
        """Validate source is one of the allowed values"""
        allowed_sources = ["all", "stackoverflow", "github", "official_doc"]
        if v not in allowed_sources:
            raise ValueError(f"Source must be one of {allowed_sources}")
        return v
    
    @validator('query')
    def validate_query(cls, v):
        """Validate query is not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class CreateTaskArgs(BaseModel):
    """Validated arguments for create_task tool"""
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Task name",
        example="Optimize database queries"
    )
    description: Optional[str] = Field(
        default="",
        max_length=1000,
        description="Task description",
        example="Improve query performance for user analytics"
    )
    priority: str = Field(
        default="medium",
        description="Task priority level",
        example="high"
    )
    
    @validator('priority')
    def validate_priority(cls, v):
        """Validate priority is one of the allowed values"""
        allowed_priorities = ["low", "medium", "high"]
        if v not in allowed_priorities:
            raise ValueError(f"Priority must be one of {allowed_priorities}")
        return v.lower()
    
    @validator('name')
    def validate_name(cls, v):
        """Validate name is not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError("Task name cannot be empty")
        return v.strip()


class GetTaskStatsArgs(BaseModel):
    """Validated arguments for get_task_stats tool (no arguments needed)"""
    pass