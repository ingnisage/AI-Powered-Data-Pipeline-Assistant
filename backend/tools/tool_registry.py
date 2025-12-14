# tools/tool_registry.py - Centralized Tool Registry
"""
Centralized registry for all available tools with metadata.
Separates tool definitions from implementations for better organization.
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class ToolRole(str, Enum):
    """Required roles for tool access."""
    GENERAL = "general"
    DATA_ENGINEER = "data_engineer"
    ML_ENGINEER = "ml_engineer"
    ANALYST = "analyst"


class ToolCategory(str, Enum):
    """Tool categories for organization."""
    DATA_ACCESS = "data_access"
    DATA_QUALITY = "data_quality"
    CODE_GENERATION = "code_generation"
    PIPELINE = "pipeline"
    SEARCH = "search"
    KNOWLEDGE = "knowledge"
    CHAT = "chat"


class ToolDefinition:
    """Structured tool definition with metadata."""
    
    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        required_role: ToolRole,
        parameters: Dict[str, Any],
        required_params: List[str]
    ):
        self.name = name
        self.description = description
        self.category = category
        self.required_role = required_role
        self.parameters = parameters
        self.required_params = required_params
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "metadata": {
                    "required_role": self.required_role.value,
                    "category": self.category.value
                },
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required_params
                }
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "required_role": self.required_role.value,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required_params
            }
        }


class ToolRegistry:
    """Central registry for all tools."""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register all default tools."""
        
        # Data Access Tools
        self.register(ToolDefinition(
            name="query_data_source",
            description="Query a data source to get sample data or schema information",
            category=ToolCategory.DATA_ACCESS,
            required_role=ToolRole.DATA_ENGINEER,
            parameters={
                "source_type": {
                    "type": "string",
                    "enum": ["database", "api", "file", "stream"],
                    "description": "Type of data source to query"
                },
                "query": {
                    "type": "string",
                    "description": "SQL query, API endpoint, or file path"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of records to return",
                    "default": 10
                }
            },
            required_params=["source_type", "query"]
        ))
        
        # Data Quality Tools
        self.register(ToolDefinition(
            name="analyze_data_quality",
            description="Analyze data quality metrics for a dataset",
            category=ToolCategory.DATA_QUALITY,
            required_role=ToolRole.DATA_ENGINEER,
            parameters={
                "dataset_id": {
                    "type": "string",
                    "description": "Identifier for the dataset"
                },
                "metrics": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["completeness", "accuracy", "consistency", "timeliness", "uniqueness"]
                    },
                    "description": "Data quality metrics to analyze"
                }
            },
            required_params=["dataset_id"]
        ))
        
        # Code Generation Tools
        self.register(ToolDefinition(
            name="generate_sql_query",
            description="Generate optimized SQL query for data analysis",
            category=ToolCategory.CODE_GENERATION,
            required_role=ToolRole.DATA_ENGINEER,
            parameters={
                "requirement": {
                    "type": "string",
                    "description": "Business requirement or analysis goal"
                },
                "database_type": {
                    "type": "string",
                    "enum": ["postgresql", "mysql", "bigquery", "snowflake", "redshift"],
                    "description": "Type of database"
                },
                "complexity": {
                    "type": "string",
                    "enum": ["simple", "intermediate", "complex"],
                    "description": "Complexity level of the query"
                }
            },
            required_params=["requirement", "database_type"]
        ))
        
        # Pipeline Tools
        self.register(ToolDefinition(
            name="schedule_data_pipeline",
            description="Schedule or trigger a data pipeline execution",
            category=ToolCategory.PIPELINE,
            required_role=ToolRole.DATA_ENGINEER,
            parameters={
                "pipeline_id": {
                    "type": "string",
                    "description": "Identifier of the pipeline to schedule"
                },
                "schedule_type": {
                    "type": "string",
                    "enum": ["immediate", "daily", "hourly", "weekly", "monthly"],
                    "description": "When to execute the pipeline"
                },
                "parameters": {
                    "type": "object",
                    "description": "Additional parameters for the pipeline"
                }
            },
            required_params=["pipeline_id"]
        ))
        
        self.register(ToolDefinition(
            name="trigger_data_pipeline",
            description="Run a background job",
            category=ToolCategory.PIPELINE,
            required_role=ToolRole.DATA_ENGINEER,
            parameters={
                "pipeline_id": {"type": "string"},
                "parameters": {"type": "object"}
            },
            required_params=["pipeline_id"]
        ))
        
        # Search Tools
        self.register(ToolDefinition(
            name="smart_search",
            description="Intelligently search the most relevant knowledge sources based on query type (StackOverflow, GitHub, official docs)",
            category=ToolCategory.SEARCH,
            required_role=ToolRole.GENERAL,
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about what to search for",
                    "enum": ["error", "code_example", "documentation", "best_practice", "all"]
                },
                "source": {
                    "type": "string",
                    "description": "Optional: restrict search to a single source",
                    "enum": ["github", "stackoverflow", "official_doc"]
                },
                "max_total_results": {
                    "type": "integer",
                    "default": 5
                }
            },
            required_params=["query"]
        ))
        
        # Knowledge Tools
        self.register(ToolDefinition(
            name="query_knowledge_base",
            description="Direct vector search in knowledge base",
            category=ToolCategory.KNOWLEDGE,
            required_role=ToolRole.GENERAL,
            parameters={
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5}
            },
            required_params=["query"]
        ))
        
        # Chat Tools
        self.register(ToolDefinition(
            name="read_chat_history",
            description="Get recent conversation history",
            category=ToolCategory.CHAT,
            required_role=ToolRole.GENERAL,
            parameters={
                "session_id": {"type": "string"},
                "limit": {"type": "integer", "default": 20}
            },
            required_params=[]
        ))
    
    def register(self, tool: ToolDefinition) -> None:
        """Register a new tool.
        
        Args:
            tool: Tool definition to register
        """
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool definition or None if not found
        """
        return self._tools.get(name)
    
    def get_all(self) -> List[ToolDefinition]:
        """Get all registered tools.
        
        Returns:
            List of all tool definitions
        """
        return list(self._tools.values())
    
    def get_by_role(self, role: ToolRole) -> List[ToolDefinition]:
        """Get tools available for a specific role.
        
        Args:
            role: User role
            
        Returns:
            List of tools accessible by the role
        """
        return [tool for tool in self._tools.values() if tool.required_role == role or tool.required_role == ToolRole.GENERAL]
    
    def get_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """Get tools in a specific category.
        
        Args:
            category: Tool category
            
        Returns:
            List of tools in the category
        """
        return [tool for tool in self._tools.values() if tool.category == category]
    
    def to_openai_format(self) -> List[Dict[str, Any]]:
        """Convert all tools to OpenAI function calling format.
        
        Returns:
            List of tool definitions in OpenAI format
        """
        return [tool.to_openai_format() for tool in self._tools.values()]
    
    def to_api_format(self) -> List[Dict[str, Any]]:
        """Convert all tools to API response format.
        
        Returns:
            List of tool definitions for API responses
        """
        return [tool.to_dict() for tool in self._tools.values()]


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance.
    
    Returns:
        ToolRegistry singleton
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
