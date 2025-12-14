# tools/base.py - Base Tool Handler Interface
"""
Base classes and interfaces for tool handlers.
All tool handlers should inherit from BaseTool for consistent implementation.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ToolResult:
    """Standardized tool execution result."""
    
    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        tool_name: str = "",
        execution_time_ms: Optional[int] = None
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.tool_name = tool_name
        self.execution_time_ms = execution_time_ms
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "success": self.success,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp.isoformat()
        }
        
        if self.success:
            result["data"] = self.data
        else:
            result["error"] = self.error
        
        if self.execution_time_ms is not None:
            result["execution_time_ms"] = self.execution_time_ms
        
        return result


class BaseTool(ABC):
    """Abstract base class for all tool handlers.
    
    Each tool implementation should inherit from this class and implement
    the execute() method with tool-specific logic.
    """
    
    def __init__(self, name: str, category: str):
        """Initialize base tool.
        
        Args:
            name: Tool name (must match tool registry)
            category: Tool category for logging
        """
        self.name = name
        self.category = category
        self.logger = logging.getLogger(f"tools.{name}")
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with execution outcome
        """
        pass
    
    async def execute_safe(self, **kwargs) -> ToolResult:
        """Execute tool with automatic error handling and timing.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with execution outcome
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Executing {self.name} with args: {list(kwargs.keys())}")
            result = await self.execute(**kwargs)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.execution_time_ms = int(execution_time)
            result.tool_name = self.name
            
            self.logger.info(f"{self.name} completed in {execution_time:.0f}ms")
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.logger.error(f"{self.name} failed after {execution_time:.0f}ms: {e}", exc_info=True)
            
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}",
                tool_name=self.name,
                execution_time_ms=int(execution_time)
            )
    
    def validate_params(self, required: list, provided: dict) -> Optional[str]:
        """Validate that all required parameters are provided.
        
        Args:
            required: List of required parameter names
            provided: Dictionary of provided parameters
            
        Returns:
            Error message if validation fails, None otherwise
        """
        missing = [param for param in required if param not in provided]
        if missing:
            return f"Missing required parameters: {', '.join(missing)}"
        return None
